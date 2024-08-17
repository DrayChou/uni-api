import json
from fastapi import HTTPException
import httpx

from log_config import logger


def update_config(config_data):
    for index, provider in enumerate(config_data["providers"]):
        model_dict = {}
        for model in provider["model"]:
            if isinstance(model, str):
                model_dict[model] = model
            if isinstance(model, dict):
                model_dict.update({new: old for old, new in model.items()})
                model_dict.update({old: old for old, new in model.items()})
        provider["model"] = model_dict
        config_data["providers"][index] = provider
    api_keys_db = config_data["api_keys"]
    api_list = [item["api"] for item in api_keys_db]
    # logger.info(json.dumps(config_data, indent=4, ensure_ascii=False))
    return config_data, api_keys_db, api_list


# 读取 YAML 配置文件
async def load_config(app):
    import yaml

    try:
        with open("./api.yaml", "r", encoding="utf-8") as f:
            # 判断是否为空文件
            conf = yaml.safe_load(f)
            # conf = None
            if conf:
                config, api_keys_db, api_list = update_config(conf)
            else:
                # logger.error("配置文件 'api.yaml' 为空。请检查文件内容。")
                config, api_keys_db, api_list = [], [], []
    except FileNotFoundError:
        logger.error("配置文件 'api.yaml' 未找到。请确保文件存在于正确的位置。")
        config, api_keys_db, api_list = [], [], []
    except yaml.YAMLError:
        logger.error("配置文件 'api.yaml' 格式不正确。请检查 YAML 格式。")
        config, api_keys_db, api_list = [], [], []

    if config != []:
        return config, api_keys_db, api_list

    import os

    # 新增：从环境变量获取配置 URL 并拉取配置
    config_url = os.environ.get("CONFIG_URL")
    if config_url:
        try:
            response = await app.state.client.get(config_url)
            # logger.info(f"Fetching config from {response.text}")
            response.raise_for_status()
            config_data = yaml.safe_load(response.text)
            # 更新配置
            # logger.info(config_data)
            if config_data:
                config, api_keys_db, api_list = update_config(config_data)
            else:
                logger.error(f"Error fetching or parsing config from {config_url}")
                config, api_keys_db, api_list = [], [], []
        except Exception as e:
            logger.error(
                f"Error fetching or parsing config from {config_url}: {str(e)}"
            )
            config, api_keys_db, api_list = [], [], []
    return config, api_keys_db, api_list


def ensure_string(item):
    if isinstance(item, (bytes, bytearray)):
        return item.decode("utf-8")
    elif isinstance(item, str):
        return item
    elif isinstance(item, dict):
        return f"data: {json.dumps(item)}\n\n"
    else:
        return str(item)


async def async_generator(items):
    for item in items:
        yield item


async def error_handling_wrapper(generator, status_code=200):
    try:
        first_item = await generator.__anext__()
        first_item_str = first_item
        logger.info(f"error_handling_wrapper first_item: {first_item}")
        
        if isinstance(first_item_str, (bytes, bytearray)):
            first_item_str = first_item_str.decode("utf-8")
        if isinstance(first_item_str, str):
            if first_item_str.startswith("data: "):
                first_item_str = first_item_str[6:]
            elif first_item_str.startswith("data:"):
                first_item_str = first_item_str[5:]
            if first_item_str.startswith("[DONE]"):
                logger.error("error_handling_wrapper [DONE]!")
                raise StopAsyncIteration
            try:
                first_item_str = json.loads(first_item_str)
            except json.JSONDecodeError:
                logger.error(
                    "error_handling_wrapper JSONDecodeError!" + repr(first_item_str)
                )
                raise StopAsyncIteration
        if isinstance(first_item_str, dict) and "error" in first_item_str:
            # 如果第一个 yield 的项是错误信息，抛出 HTTPException
            raise HTTPException(
                status_code=status_code, detail=f"{first_item_str}"[:300]
            )

        # 如果不是错误，创建一个新的生成器，首先 yield 第一个项，然后 yield 剩余的项
        async def new_generator():
            yield ensure_string(first_item)
            async for item in generator:
                yield ensure_string(item)

        return new_generator()

    except StopAsyncIteration:
        raise HTTPException(
            status_code=status_code, detail="data: {'error': 'No data returned'}"
        )


def post_all_models(token, config, api_list):
    all_models = []
    unique_models = set()

    if token not in api_list:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key")
    api_index = api_list.index(token)
    if config["api_keys"][api_index]["model"]:
        for model in config["api_keys"][api_index]["model"]:
            if "/" in model:
                provider = model.split("/")[0]
                model = model.split("/")[1]
                if model == "*":
                    for provider_item in config["providers"]:
                        if provider_item["provider"] != provider:
                            continue
                        for model_item in provider_item["model"].keys():
                            if model_item not in unique_models:
                                unique_models.add(model_item)
                                model_info = {
                                    "id": model_item,
                                    "object": "model",
                                    "created": 1720524448858,
                                    "owned_by": "uni-api",
                                    # "owned_by": provider_item['provider']
                                }
                                all_models.append(model_info)
                else:
                    for provider_item in config["providers"]:
                        if provider_item["provider"] != provider:
                            continue
                        for model_item in provider_item["model"].keys():
                            if model_item not in unique_models and model_item == model:
                                unique_models.add(model_item)
                                model_info = {
                                    "id": model_item,
                                    "object": "model",
                                    "created": 1720524448858,
                                    "owned_by": "uni-api",
                                }
                                all_models.append(model_info)
                continue

            if model not in unique_models:
                unique_models.add(model)
                model_info = {
                    "id": model,
                    "object": "model",
                    "created": 1720524448858,
                    "owned_by": model,
                }
                all_models.append(model_info)

    return all_models


def get_all_models(config):
    all_models = []
    unique_models = set()

    for provider in config["providers"]:
        for model in provider["model"].keys():
            if model not in unique_models:
                unique_models.add(model)
                model_info = {
                    "id": model,
                    "object": "model",
                    "created": 1720524448858,
                    "owned_by": "uni-api",
                }
                all_models.append(model_info)

    return all_models
