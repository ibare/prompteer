"""
Proxy objects for dynamic attribute access in prompteer.

Enables dot-notation access to prompts: prompts.myPrompt.question.user()

Resolution rules
----------------
* Names are matched ignoring case and unicode normal form, so the same code
  resolves identically on macOS, Linux and Windows.
* A static file or directory always wins over a dynamic ``[param]`` route.
* Dynamic routing is recursive: ``[param]`` directories may nest, and static
  directories may sit between them.
* At a ``[param]`` level the fallback order is ``<value>/`` then ``default/``
  then ``default.md`` (the last only when a single segment remains). A failure
  there is final -- it is not propagated to an outer ``[param]`` level.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable, Literal

from prompteer.exceptions import (
    DynamicParameterError,
    PrompteerError,
    PromptNotFoundError,
)
from prompteer.path_utils import (
    camel_to_kebab,
    extract_param_name,
    find_entry,
    format_candidates,
    get_dir_index,
    iter_dynamic_dirs,
    validate_param_value,
)

#: 심볼릭 링크 순환이나 병적으로 깊은 트리에서 무한 재귀를 막는다.
MAX_RESOLUTION_DEPTH = 64

#: default 폴백에 쓰이는 이름 (디렉터리 `default/` 와 파일 `default.md` 양쪽)
DEFAULT_NAME = "default"


# ---------------------------------------------------------------------------
# 이름 매칭
# ---------------------------------------------------------------------------


def _name_candidates(name: str) -> list[str]:
    """Build the filesystem name candidates for an attribute name.

    ``myPrompt`` is tried as ``my-prompt`` first (the documented convention)
    and then verbatim, so ``MyPrompt/`` and ``my-prompt/`` are both reachable.

    Args:
        name: Attribute name as written in Python

    Returns:
        Candidate filesystem names, most conventional first
    """
    kebab = camel_to_kebab(name)
    if kebab == name:
        return [name]
    return [kebab, name]


def _lookup(
    directory: Path,
    name: str,
    kind: Literal["dir", "file"],
    suffix: str = "",
) -> Path | None:
    """Find a child entry for an attribute name.

    Two spellings are tried: the kebab-case conversion (the documented
    convention) and the attribute name verbatim. Ordering is by match quality,
    not by candidate: every spelling gets an exact pass before any of them may
    match by normalization. Otherwise ``camel_to_kebab("Chat") == "chat"``
    would let the derived spelling claim ``chat/`` on a case-sensitive
    filesystem even though the caller wrote ``Chat`` and ``Chat/`` exists.
    Within the exact pass the verbatim spelling wins, since that is the name
    the caller actually typed.

    Args:
        directory: Parent directory
        name: Attribute name
        kind: Restrict the match to directories or files
        suffix: Appended to each candidate, e.g. ``".md"``

    Returns:
        Matching path, or None
    """
    candidates = _name_candidates(name)

    for candidate in reversed(candidates):
        hit = find_entry(directory, f"{candidate}{suffix}", kind, exact_only=True)
        if hit is not None:
            return hit

    for candidate in candidates:
        hit = find_entry(directory, f"{candidate}{suffix}", kind)
        if hit is not None:
            return hit

    return None


def _find_dir(directory: Path, name: str) -> Path | None:
    """Find a subdirectory matching an attribute name.

    Args:
        directory: Parent directory
        name: Attribute name

    Returns:
        Matching directory, or None
    """
    return _lookup(directory, name, "dir")


def _find_md(directory: Path, name: str) -> Path | None:
    """Find a ``.md`` prompt file matching an attribute name.

    Args:
        directory: Parent directory
        name: Attribute name

    Returns:
        Matching file, or None
    """
    return _lookup(directory, name, "file", ".md")


# ---------------------------------------------------------------------------
# 렌더링
# ---------------------------------------------------------------------------


def _render_prompt_file(
    file_path: Path,
    kwargs: dict[str, Any],
    encoding: str,
    guard_params: Iterable[str] = (),
    route_errors: dict[str, PromptNotFoundError] | None = None,
    routed: dict[str, str] | None = None,
) -> str:
    """Read a prompt file and render it with the given variables.

    Args:
        file_path: Path to the prompt file
        kwargs: Variables to substitute in the template
        encoding: File encoding
        guard_params: Dynamic parameter names seen while resolving this prompt.
            Any of these left in ``kwargs`` that the prompt does not declare as
            a template variable indicates a routing argument that silently did
            nothing, which is reported instead of being ignored.
        route_errors: Routing failures that were set aside because a static
            prompt matched instead. If the unused parameter belongs to one of
            them, that failure is the real cause and is raised instead.
        routed: Routing parameters consumed on the way to this prompt, as the
            caller supplied them. They are exposed to the template so a prompt
            can mention the route it was selected by. They cannot collide with
            ``kwargs``: routing pops the name before rendering, and Python
            forbids passing the same keyword twice.

    Returns:
        Rendered prompt string

    Raises:
        DynamicParameterError: If a routing parameter went unused
        TemplateVariableError: If a required variable is missing
    """
    from prompteer.metadata import get_type_default, parse_metadata
    from prompteer.template import extract_variables, render_template_with_defaults

    content = file_path.read_text(encoding=encoding)
    metadata, body = parse_metadata(content)

    # 가드는 호출자가 넘긴 인자만 봐야 한다. 라우팅 값을 먼저 합치면
    # 소비된 파라미터를 "안 쓰인 인자" 로 오인한다.
    if guard_params:
        _check_unused_params(
            file_path, kwargs, guard_params, metadata, body, route_errors
        )

    # Build defaults from metadata
    defaults = {}
    for var_name, var_info in metadata.variables.items():
        defaults[var_name] = get_type_default(var_info.type)

    variables = {**routed, **kwargs} if routed else kwargs

    # 아래 두 분기는 호출자 인자(kwargs)로 판단한다. 라우팅 값을 섞으면
    # 인자 없이 호출했을 때 본문을 그대로 돌려주던 동작이 바뀐다.
    # If no variables provided and no variables in template, return body as-is
    if not kwargs and not metadata.variables:
        if not extract_variables(body):
            return body

    # Render with variables and defaults
    try:
        return render_template_with_defaults(body, variables, defaults)
    except Exception:
        # Fallback: if there's an error and no kwargs, return body
        if not kwargs:
            return body
        raise


def _check_unused_params(
    file_path: Path,
    kwargs: dict[str, Any],
    guard_params: Iterable[str],
    metadata: Any,
    body: str,
    route_errors: dict[str, PromptNotFoundError] | None = None,
) -> None:
    """Raise if a dynamic routing parameter was passed but never consumed.

    A static path can win over a dynamic one, in which case a ``[param]``
    argument would quietly be treated as a template variable and the caller
    would get a different prompt than they asked for.

    Args:
        file_path: Resolved prompt file, used in the error message
        kwargs: Variables left after routing consumed its parameters
        guard_params: Parameter names seen during resolution
        metadata: Parsed frontmatter of the prompt
        body: Prompt body, scanned for ``{variable}`` placeholders
        route_errors: Routing failures set aside during resolution

    Raises:
        PromptNotFoundError: If the unused parameter belongs to a dynamic route
            that was tried and failed
        DynamicParameterError: If an unconsumed routing parameter is present
    """
    from prompteer.template import extract_variables

    leftover = {key for key in kwargs if key in set(guard_params)}
    if not leftover:
        return

    declared = set(metadata.variables) | set(extract_variables(body))
    offenders = sorted(leftover - declared)
    if not offenders:
        return

    name = offenders[0]

    # 그 파라미터의 라우트를 실제로 시도했다가 실패한 것이라면,
    # "안 쓰였다" 보다 그 실패 사유가 정확한 원인이다.
    if route_errors and name in route_errors:
        raise route_errors[name]

    raise DynamicParameterError(
        parameter=name,
        message=(
            f"Parameter {name!r} was not used: {file_path.name} was reached "
            f"through a static path, so no [{name}] directory consumed it and "
            f"the prompt does not declare {name!r} as a template variable. "
            f"Remove the argument, or check that the route you meant exists."
        ),
    )


# ---------------------------------------------------------------------------
# 해석 (resolution)
# ---------------------------------------------------------------------------


class _Resolution:
    """Mutable bookkeeping for a single resolution attempt."""

    def __init__(self, base_path: Path) -> None:
        """Initialize resolution state.

        Args:
            base_path: Root of the prompt tree, used to shorten paths in errors
        """
        self.base_path = base_path
        self.tried: list[str] = []
        self.seen_params: set[str] = set()
        self.consumed: dict[str, str] = {}
        # 동적 라우트가 실패했지만 정적 대안이 있어 보류한 오류.
        # 정적 결과가 그 파라미터를 쓰지 않으면 이쪽이 진짜 원인이다.
        self.route_errors: dict[str, PromptNotFoundError] = {}

    def rel(self, path: Path) -> str:
        """Render a path relative to the prompt root for error messages.

        Args:
            path: Path to shorten

        Returns:
            Relative path string, or the absolute path if it is outside the root
        """
        try:
            return str(path.relative_to(self.base_path))
        except ValueError:
            return str(path)

    def note(self, directory: Path, pending: tuple[str, ...], reason: str = "") -> None:
        """Record a candidate path that was tried and did not match.

        Args:
            directory: Directory the lookup started from
            pending: Remaining attribute segments
            reason: Optional explanation appended in parentheses
        """
        target = "/".join(pending[:-1] + (pending[-1] + ".md",)) if pending else ""
        entry = f"{self.rel(directory)}/{target}" if target else self.rel(directory)
        if reason:
            entry = f"{entry}  ({reason})"
        self.tried.append(entry)


def _resolve(
    directory: Path,
    pending: tuple[str, ...],
    kwargs: dict[str, Any],
    state: _Resolution,
    depth: int,
) -> Path | None:
    """Resolve remaining attribute segments to a prompt file.

    Args:
        directory: Directory to resolve from
        pending: Remaining attribute segments, at least one
        kwargs: Caller arguments; consumed routing parameters are popped
        state: Resolution bookkeeping
        depth: Current recursion depth

    Returns:
        The resolved prompt file, or None when this branch has no match and the
        caller may try another one

    Raises:
        PromptNotFoundError: When a dynamic level was entered and exhausted
        TypeError: When a required routing parameter was not supplied
        PrompteerError: When the tree is deeper than MAX_RESOLUTION_DEPTH
    """
    if depth > MAX_RESOLUTION_DEPTH:
        raise PrompteerError(
            f"Prompt resolution exceeded {MAX_RESOLUTION_DEPTH} levels at "
            f"{state.rel(directory)}; check for a symlink loop in the prompt tree."
        )

    # 이 레벨의 [param] 은 실제로 내려가지 않더라도 기록해 둔다.
    # 정적 경로가 이겨서 라우팅 인자가 조용히 무시되는 경우를 잡기 위해서다.
    dynamic_dirs = iter_dynamic_dirs(directory)
    for dynamic_dir in dynamic_dirs:
        state.seen_params.add(extract_param_name(dynamic_dir.name))

    head, rest = pending[0], pending[1:]

    # 같은 이름이 정적으로도 동적으로도 존재할 수 있다. 호출자가 이 레벨의
    # 라우팅 파라미터를 실제로 넘겼다면 그 라우트를 원한 것이므로 동적을 먼저
    # 시도하고, 넘기지 않았다면 정적이 우선한다. 어느 쪽이든 결과는 파일시스템
    # 순회 순서가 아니라 호출 인자만으로 결정된다.
    static_match = _find_dir(directory, head) if rest else _find_md(directory, head)
    prefer_dynamic = bool(dynamic_dirs) and (
        extract_param_name(dynamic_dirs[0].name) in kwargs
    )
    deferred_error: PromptNotFoundError | None = None

    # A. 요청된 동적 라우트
    if prefer_dynamic:
        trial = dict(kwargs)
        try:
            hit = _resolve_dynamic(dynamic_dirs[0], pending, trial, state, depth + 1)
        except PromptNotFoundError as error:
            if static_match is None:
                raise
            # 정적 대안이 있으므로 아직 실패로 확정하지 않는다.
            deferred_error = error
            state.route_errors.setdefault(
                extract_param_name(dynamic_dirs[0].name), error
            )
        else:
            kwargs.clear()
            kwargs.update(trial)
            return hit

    # B. 정적
    if static_match is not None:
        if rest:
            static_hit = _resolve(static_match, rest, kwargs, state, depth + 1)
            if static_hit is not None:
                return static_hit
        else:
            return static_match
    elif not rest:
        state.note(directory, pending)

    # C. 요청되지 않은 동적 라우트 (파라미터 누락이면 TypeError 로 안내)
    if dynamic_dirs and not prefer_dynamic:
        return _resolve_dynamic(dynamic_dirs[0], pending, kwargs, state, depth + 1)

    if deferred_error is not None:
        raise deferred_error

    return None


def _resolve_dynamic(
    dynamic_dir: Path,
    pending: tuple[str, ...],
    kwargs: dict[str, Any],
    state: _Resolution,
    depth: int,
) -> Path:
    """Resolve through a ``[param]`` directory.

    Fallback order is ``<value>/`` then ``default/`` then ``default.md``, the
    last only when a single segment remains -- a single file cannot stand in
    for a whole subtree. Failure here is final and is not propagated to an
    outer dynamic level.

    Args:
        dynamic_dir: The ``[param]`` directory
        pending: Remaining attribute segments
        kwargs: Caller arguments; the routing parameter is popped
        state: Resolution bookkeeping
        depth: Current recursion depth

    Returns:
        The resolved prompt file

    Raises:
        PromptNotFoundError: If no value, default subtree or default file matches
        TypeError: If the routing parameter was not supplied
        DynamicParameterError: If the routing parameter value is unusable
    """
    param_name = extract_param_name(dynamic_dir.name)
    state.seen_params.add(param_name)

    if param_name not in kwargs:
        available = _available_values(dynamic_dir)
        raise TypeError(
            f"Missing required parameter: {param_name} "
            f"(dynamic route {state.rel(dynamic_dir)}, "
            f"available values: {format_candidates(available)})"
        )

    value = validate_param_value(kwargs.pop(param_name), param_name)
    state.consumed[param_name] = value

    # 1. <value>/ 하위 트리
    value_dir = _find_dir(dynamic_dir, value)
    if value_dir is not None:
        hit = _resolve(value_dir, pending, kwargs, state, depth + 1)
        if hit is not None:
            return hit
    else:
        state.note(dynamic_dir / value, pending, f"no {param_name}={value!r} directory")

    # 2. default/ 하위 트리
    default_dir = _find_dir(dynamic_dir, DEFAULT_NAME)
    if default_dir is not None:
        hit = _resolve(default_dir, pending, kwargs, state, depth + 1)
        if hit is not None:
            return hit
    else:
        state.note(dynamic_dir / DEFAULT_NAME, pending, "no default/ directory")

    # 3. default.md — 남은 세그먼트가 하나일 때만.
    #    파일 하나는 extra/user 와 extra/system 을 구분할 수 없으므로,
    #    경로가 남아 있으면 조용히 폴백하지 않고 실패시킨다.
    if len(pending) == 1:
        default_file = _find_md(dynamic_dir, DEFAULT_NAME)
        if default_file is not None:
            return default_file
        state.tried.append(f"{state.rel(dynamic_dir)}/default.md")
    else:
        state.tried.append(
            f"{state.rel(dynamic_dir)}/default.md  "
            f"(skipped: path has {len(pending)} segments)"
        )

    # 4. 바깥쪽 [param] 레벨로 전파하지 않는다.
    target = "/".join(pending)
    raise PromptNotFoundError(
        path=f"{state.rel(dynamic_dir)}/{target}",
        message=(f"No prompt found for {target} with {param_name}={value!r}"),
        tried=state.tried,
    )


def _available_values(dynamic_dir: Path) -> list[str]:
    """List the value directories of a dynamic directory.

    Args:
        dynamic_dir: The ``[param]`` directory

    Returns:
        Sorted value directory names, excluding the default fallback
    """
    values: list[str] = []
    for names in get_dir_index(dynamic_dir).values():
        for name in names:
            if name == DEFAULT_NAME:
                continue
            if (dynamic_dir / name).is_dir():
                values.append(name)
    return sorted(values)


def _is_reachable(directory: Path, name: str, depth: int = 0) -> bool:
    """Check whether a name could appear below a directory via dynamic routes.

    Used to fail fast on typos: an attribute that matches nothing anywhere in
    the reachable subtree raises at attribute-access time instead of deferring
    the error to the call.

    Args:
        directory: Directory to search from
        name: Attribute name to look for
        depth: Current recursion depth

    Returns:
        True if some reachable directory holds a matching entry
    """
    if depth > MAX_RESOLUTION_DEPTH:
        return False

    if _find_dir(directory, name) is not None or _find_md(directory, name) is not None:
        return True

    for dynamic_dir in iter_dynamic_dirs(directory):
        # default.md 는 이름을 가리지 않는 catch-all 이므로 어떤 이름이든 도달 가능하다.
        if _find_md(dynamic_dir, DEFAULT_NAME) is not None:
            return True

        for names in get_dir_index(dynamic_dir).values():
            for entry in names:
                child = dynamic_dir / entry
                if child.is_dir() and _is_reachable(child, name, depth + 1):
                    return True

    return False


# ---------------------------------------------------------------------------
# 프록시
# ---------------------------------------------------------------------------


class PromptProxy:
    """Proxy object that enables dynamic attribute access to prompts.

    Attributes are resolved to either:
    - Subdirectories: Return another PromptProxy
    - Files (*.md): Return a callable that renders the prompt
    - Prompts behind a ``[param]`` route: Return a DeferredPromptProxy that
      resolves once the routing parameters are supplied at call time
    """

    _base_path: Path
    _current_path: Path
    _encoding: str

    def __init__(
        self,
        base_path: Path,
        current_path: Path,
        encoding: str = "utf-8",
    ) -> None:
        """Initialize a PromptProxy.

        Args:
            base_path: Root directory of all prompts
            current_path: Current directory path
            encoding: File encoding for reading prompts
        """
        object.__setattr__(self, "_base_path", base_path)
        object.__setattr__(self, "_current_path", current_path)
        object.__setattr__(self, "_encoding", encoding)

    def __getattr__(self, name: str) -> Any:
        """Get attribute by name, resolving to directory, file or dynamic route.

        Args:
            name: Attribute name in camelCase

        Returns:
            PromptProxy for directories, a callable for files, or a
            DeferredPromptProxy for prompts behind a dynamic route

        Raises:
            PromptNotFoundError: If the name matches nothing reachable
        """
        if name.startswith("_"):
            # dunder 조회나 hasattr 탐색이 동적 라우팅으로 새는 것을 막는다.
            raise AttributeError(name)

        # 이 레벨에 [param] 이 있으면 정적으로 매칭되는 이름이라도 해석을 미룬다.
        # 정적과 동적 중 무엇을 택할지는 호출 인자를 봐야 정해지기 때문이다.
        # 동적 디렉터리가 없는 트리는 지금까지처럼 즉시 해석된다.
        if iter_dynamic_dirs(self._current_path):
            if _is_reachable(self._current_path, name):
                return DeferredPromptProxy(
                    self._base_path, self._current_path, (name,), self._encoding
                )
        else:
            dir_path = _find_dir(self._current_path, name)
            if dir_path is not None:
                return PromptProxy(self._base_path, dir_path, self._encoding)

            file_path = _find_md(self._current_path, name)
            if file_path is not None:
                return self._create_prompt_callable(file_path)

        relative_path = self._current_path.relative_to(self._base_path)
        path_name = camel_to_kebab(name)
        full_attr_path = (
            f"{relative_path}/{path_name}" if str(relative_path) != "." else path_name
        )
        raise PromptNotFoundError(
            path=str(full_attr_path),
            message=(
                f"Prompt not found: {full_attr_path} "
                f"(looking for directory or {path_name}.md)"
            ),
        )

    def _create_prompt_callable(self, file_path: Path) -> Callable[..., str]:
        """Create a callable that reads and renders a prompt file.

        Args:
            file_path: Path to the prompt file

        Returns:
            Callable that accepts keyword arguments and returns rendered prompt
        """
        encoding = self._encoding

        def prompt_renderer(**kwargs: Any) -> str:
            """Read and render the prompt with provided variables.

            Args:
                **kwargs: Variables to substitute in the template

            Returns:
                Rendered prompt string

            Raises:
                TemplateVariableError: If required variables are missing
            """
            return _render_prompt_file(file_path, kwargs, encoding)

        prompt_renderer.__name__ = file_path.stem
        return prompt_renderer

    def _render_prompt(self, file_path: Path, kwargs: dict[str, Any]) -> str:
        """Render a prompt file with variables.

        Args:
            file_path: Path to the prompt file
            kwargs: Variables to substitute in the template

        Returns:
            Rendered prompt string
        """
        return _render_prompt_file(file_path, kwargs, self._encoding)

    def __setattr__(self, name: str, value: Any) -> None:
        """Prevent setting attributes on proxy objects.

        Args:
            name: Attribute name
            value: Attribute value

        Raises:
            AttributeError: Always, as proxy objects are read-only
        """
        raise AttributeError(
            "Cannot set attributes on PromptProxy. "
            "Prompts are read-only and loaded from the filesystem."
        )

    def __repr__(self) -> str:
        """Return string representation of the proxy.

        Returns:
            String representation
        """
        relative_path = self._current_path.relative_to(self._base_path)
        return f"PromptProxy({relative_path})"


class DeferredPromptProxy:
    """Proxy for a prompt that sits behind one or more ``[param]`` routes.

    The path cannot be resolved at attribute-access time because the routing
    parameters only arrive with the call, so segments are accumulated and the
    whole path is resolved in :meth:`__call__`.

    Example:
        >>> # prompts/q/[type]/basic/extra/user.md
        >>> prompts.q.extra.user(type="basic")  # doctest: +SKIP
    """

    _base_path: Path
    _start_path: Path
    _pending: tuple[str, ...]
    _encoding: str

    def __init__(
        self,
        base_path: Path,
        start_path: Path,
        pending: tuple[str, ...],
        encoding: str = "utf-8",
    ) -> None:
        """Initialize a deferred proxy.

        Args:
            base_path: Root directory of all prompts
            start_path: Directory where deferred resolution begins
            pending: Attribute segments accumulated so far
            encoding: File encoding for reading prompts
        """
        object.__setattr__(self, "_base_path", base_path)
        object.__setattr__(self, "_start_path", start_path)
        object.__setattr__(self, "_pending", pending)
        object.__setattr__(self, "_encoding", encoding)

    def __getattr__(self, name: str) -> DeferredPromptProxy:
        """Accumulate another path segment.

        Args:
            name: Attribute name in camelCase

        Returns:
            A new deferred proxy with the segment appended

        Raises:
            AttributeError: For private names, so introspection behaves normally
        """
        if name.startswith("_"):
            raise AttributeError(name)
        return DeferredPromptProxy(
            self._base_path,
            self._start_path,
            self._pending + (name,),
            self._encoding,
        )

    def __call__(self, **kwargs: Any) -> str:
        """Resolve the accumulated path and render the prompt.

        Args:
            **kwargs: Routing parameters plus template variables

        Returns:
            Rendered prompt string

        Raises:
            TypeError: If a routing parameter is missing
            DynamicParameterError: If a routing parameter value is unusable
            PromptNotFoundError: If no prompt matches the supplied route
        """
        state = _Resolution(self._base_path)
        variables = dict(kwargs)

        file_path = _resolve(self._start_path, self._pending, variables, state, 0)
        if file_path is None:
            target = "/".join(self._pending)
            raise PromptNotFoundError(
                path=f"{state.rel(self._start_path)}/{target}",
                message=f"Prompt not found: {target}",
                tried=state.tried,
            )

        return _render_prompt_file(
            file_path,
            variables,
            self._encoding,
            guard_params=state.seen_params,
            route_errors=state.route_errors,
            routed=state.consumed,
        )

    def __setattr__(self, name: str, value: Any) -> None:
        """Prevent setting attributes on proxy objects.

        Args:
            name: Attribute name
            value: Attribute value

        Raises:
            AttributeError: Always, as proxy objects are read-only
        """
        raise AttributeError(
            "Cannot set attributes on DeferredPromptProxy. "
            "Prompts are read-only and loaded from the filesystem."
        )

    def __repr__(self) -> str:
        """Return string representation of the deferred proxy.

        Returns:
            String representation
        """
        try:
            start = self._start_path.relative_to(self._base_path)
        except ValueError:
            start = self._start_path
        return f"DeferredPromptProxy({start}, pending={'.'.join(self._pending)})"
