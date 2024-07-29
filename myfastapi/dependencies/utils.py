from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Union

import inspect
import re

from copy import deepcopy

from fastapi import Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi._compat import lenient_issubclass
from httpx import QueryParams
from pydantic import BaseConfig, BaseModel
from pydantic.error_wrappers import ErrorWrapper
from pydantic.errors import MissingError
from pydantic.fields import ModelField, Undefined

from myfastapi.dependencies.models import Dependant

def get_dependant(
    *,
    path: str,
    call: Callable[..., Any],
) -> None:
    path_param_names = get_path_param_names(path)
    endpoint_signature = inspect.signature(call)
    signature_params = endpoint_signature.parameters
    dependant = Dependant(call=call, path=path)
    for param_name, param in signature_params.items():
        param_field = get_param_field(
            param=param, param_name=param_name
        )
        if param_name in path_param_names: dependant.path_params.append(param_field)
        elif (lenient_issubclass(param_field.type_, (list, set, tuple, dict)) or
            lenient_issubclass(param_field.type_, BaseModel)
        ): dependant.body_params.append(param_field)
        else: dependant.query_params.append(param_field)

def get_path_param_names(path: str) -> Set[str]:
    return set(re.findall("{(.*?)}", path))

def get_param_field(
    param: inspect.Parameter,
    param_name: str
) -> ModelField:
    default_value: Any = Undefined
    if not param.default == param.empty: default_value = param.default
    required = True
    if default_value is not Undefined: required = False
    annotation: Any = Any
    if not param.annotation == param.empty:
        annotation = param.annotation
    field = ModelField(
        name=param_name,
        type_=annotation,
        default=default_value,
        class_validators=None,
        required=required,
        model_config=BaseConfig,
    )
    
    return field

async def solve_dependencies(
    *,
    request: Request,
    dependant: Dependant,
    body: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[ErrorWrapper], Response]:
    values: Dict[str, any] = {}
    errors: List[ErrorWrapper] = []

    path_values, path_errors = request_params_to_args(
        dependant.path_params, request.path_params
    )
    query_values, query_errors = request_params_to_args(
        dependant.query_params, request.query_params
    )
    values.update(path_values)
    values.update(query_values)
    errors += path_errors + query_errors

    if dependant.body_params:
        (
            body_values,
            body_errors,
        ) = await request_body_to_args(  # body_params checked above
            required_params=dependant.body_params, received_body=body
        )
        values.update(body_values)
        errors.extend(body_errors)
    return values, errors

def request_params_to_args(
    required_params: Sequence[ModelField],
    received_params: Union[Mapping[str, Any], QueryParams]
) -> Tuple[Dict[str, Any], List[ErrorWrapper]]:
    values: Dict[str, Any] = {}
    errors: List[ErrorWrapper] = []
    for field in required_params:
        value = received_params.get(field.alias)
        if value is None:
            if field.required:
                errors.append(ErrorWrapper(
                    MissingError(),
                    loc=field.alias)
                    )
            else: values[field.name] = deepcopy(field.default)
            continue

        v_, errors_ = field.validate(value, values, loc=field.alias)

        if isinstance(errors_, ErrorWrapper):
            errors.append(errors_)
        elif isinstance(errors_, list):
            errors.extend(errors_)
        else:
            values[field.name] = v_
    return values, errors

async def request_body_to_args(
    required_params: List[ModelField],
    received_body: Union[Dict[str, any], None],
) -> Tuple[Dict[str, any], List[ErrorWrapper]]:
    values: Dict[str, Any] = {}
    errors: List[ErrorWrapper] = []
    if required_params:
        field_alias_omitted = len(required_params)
        if field_alias_omitted == 1:
            field = required_params[0]
            received_body = {field.alias: received_body}

        for field in required_params:
            if field_alias_omitted:
                loc = ("body",)
            else:
                loc = ("body", field.alias)
            value: Optional[Any] = None
            if received_body is not None:
                try: value = received_body.get(field.alias)
                except AttributeError:
                    errors.append(ErrorWrapper(MissingError(), loc=loc))
                    continue
            if value is None:
                if field.required: errors.append(ErrorWrapper(MissingError(), loc=loc))
                else: values[field.name] = deepcopy(field.default)
                continue

            v_, errors_ = field.validate(value, values, loc=loc)

            if isinstance(errors_, ErrorWrapper):
                errors.append(errors_)
            elif isinstance(errors_, list):
                errors.extend(errors_)
            else:
                values[field.name] = v_
    return values, errors

async def run_endpoint_function(
    *, dependant: Dependant, values: List[str, Any], is_coroutine: bool
) -> Any:
    assert dependant.call is not None, "dependant.call must be a function"

    if is_coroutine:
        return await dependant.call(**values)
    else:
        return await run_in_threadpool(dependant.call, **values)