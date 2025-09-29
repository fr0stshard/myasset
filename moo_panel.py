import os
import re
import json
import time
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import streamlit as st

APP_TITLE = "MooFarmPrivate Config Editor (Full)"
DEFAULT_HIKKA_DIR = "/home/ubuntu/Hikka-master"

# Предустановленные варианты из кода модуля
ALLOWED_BOTS = ["1606812809", "6467105350", "6396922937", "5641915741"]  # + можно добавить "6770881933"
ALLOWED_NPCS = ["npc_belka", "npc_jabomraz", "npc_edinorog", "npc_djun", "npc_djun_farm", "npc_chick", "npc_bear", "npc_ejik"]
ALLOWED_EAT_CMDS = ["/cow", "му корова", "мук"]
ALLOWED_MILK_CMDS = ["/cow", "му корова", "мук"]
# craft_comm в коде как Choice, paste содержит заглушки; оставим строковый ввод + подсказки:
ALLOWED_CRAFT_COMM_SUGGEST = ["мув"]  # из paste для default
# forest_comm MultiChoice в коде; оставим список-подсказку:
ALLOWED_FOREST_COMM = ["мулс"]

# Поля ModuleConfig → (тип, дефолт, допускается_мультивыбор, варианты)
# Типы: bool, int, str, list[str]
FIELD_SPEC: Dict[str, Tuple[str, Any, bool, List[str]]] = {
    # Общие/прочие
    "config_debug_diff_msg": ("list[str]", [], True, ["Redis", "Forest", "Eating", "Crafting", "State", "General"]),
    "config_user_tz": ("str", "UTC", False, []),
    "config_debug_msg": ("bool", False, False, []),
    "config_bot_deletemsg_inbot": ("bool", False, False, []),
    "config_bot_send_logs": ("str", "me", False, ["False", "me", "default"]),
    "config_redis_cloud_link": ("str", "", False, []),
    "config_bot_used_bot": ("list[str]", [], True, ALLOWED_BOTS),
    "config_bot_used_chat_id": ("int", 0, False, []),

    # Автоеда
    "config_bot_auto_eat": ("bool", False, False, []),
    "config_bot_auto_eating_forest": ("bool", False, False, []),
    "config_bot_eat_use_count": ("int", 1, False, []),
    "config_bot_eat_use_item": ("str", "брокколи", False, []),
    "config_bot_eat_lvl": ("int", 50, False, []),
    "config_bot_auto_eat_command": ("list[str]", [], True, ALLOWED_EAT_CMDS),

    # Автодойка
    "config_bot_auto_milk": ("bool", False, False, []),
    "config_bot_auto_milk_command": ("list[str]", [], True, ALLOWED_MILK_CMDS),

    # Автокрафт
    "config_bot_auto_craft": ("bool", False, False, []),
    "config_bot_auto_craft_count": ("int", 50, False, []),
    "config_bot_auto_craft_item_name": ("str", "масло", False, []),
    "config_bot_auto_craft_command": ("str", "мув", False, ALLOWED_CRAFT_COMM_SUGGEST),

    # Автолес
    "config_bot_auto_forest": ("bool", False, False, []),
    "config_bot_auto_forest_command": ("list[str]", ["мулс"], True, ALLOWED_FOREST_COMM),
    "config_bot_auto_forest_skip_npc": ("bool", True, False, []),
    "config_bot_autoforest_npcs": ("list[str]", [], True, ALLOWED_NPCS),

    # Скин
    "config_bot_skin_show": ("bool", False, False, []),
    "config_bot_skin_strings_id": ("int", 5395592741939849449, False, []),
    "config_bot_skin_strings_hash": ("int", -7011006528981204019, False, []),
    "config_bot_skin_strings_bytes": ("str", "AQAAClpn9Gn8lOq0lTYlXzF9lctkuIA3lNI=", False, []),

    # Кактус
    "config_bot_auto_cactus": ("bool", True, False, []),
    "config_bot_auto_cactus_water_drink": ("bool", True, False, []),
    "config_bot_auto_cactus_water_drink_lvl": ("int", 50, False, []),
    "config_bot_auto_cactus_water_drink_click": ("int", 1, False, []),

    # Курятник/телята
    "config_bot_auto_baby_tabs": ("bool", False, False, []),
    "config_bot_auto_chick_house_chick_count": ("int", 0, False, []),
    "config_bot_auto_chick_house": ("bool", True, False, []),
    "config_bot_auto_chick_house_water": ("bool", True, False, []),
    "config_bot_auto_chick_house_gather": ("bool", True, False, []),

    # Humanizer — craft
    "craft_min_day": ("int", 300, False, []),
    "craft_max_day": ("int", 1800, False, []),
    "craft_min_night": ("int", 1200, False, []),
    "craft_max_night": ("int", 3600, False, []),
    "craft_click_min_day": ("int", 1, False, []),
    "craft_click_max_day": ("int", 4, False, []),
    "craft_click_min_night": ("int", 2, False, []),
    "craft_click_max_night": ("int", 6, False, []),
    "craft_state_min_day": ("int", 1, False, []),
    "craft_state_max_day": ("int", 30, False, []),
    "craft_state_min_night": ("int", 30, False, []),
    "craft_state_max_night": ("int", 60, False, []),

    # Humanizer — eat
    "eat_min_day": ("int", 1, False, []),
    "eat_max_day": ("int", 300, False, []),
    "eat_min_night": ("int", 300, False, []),
    "eat_max_night": ("int", 2100, False, []),
    "eat_click_min_day": ("int", 1, False, []),
    "eat_click_max_day": ("int", 7, False, []),
    "eat_click_min_night": ("int", 2, False, []),
    "eat_click_max_night": ("int", 10, False, []),
    "eat_state_min_day": ("int", 1, False, []),
    "eat_state_max_day": ("int", 1, False, []),
    "eat_state_min_night": ("int", 30, False, []),
    "eat_state_max_night": ("int", 2100, False, []),

    # Humanizer — forest
    "forest_min_day": ("int", 72, False, []),
    "forest_max_day": ("int", 1200, False, []),
    "forest_min_night": ("int", 130, False, []),
    "forest_max_night": ("int", 3600, False, []),
    "forest_click_min_day": ("int", 1, False, []),
    "forest_click_max_day": ("int", 5, False, []),
    "forest_click_min_night": ("int", 2, False, []),
    "forest_click_max_night": ("int", 12, False, []),
    "forest_npc_min_day": ("int", 1, False, []),
    "forest_npc_max_day": ("int", 30, False, []),
    "forest_npc_min_night": ("int", 30, False, []),
    "forest_npc_max_night": ("int", 60, False, []),
    "forest_state_min_day": ("int", 1, False, []),
    "forest_state_max_day": ("int", 30, False, []),
    "forest_state_min_night": ("int", 30, False, []),
    "forest_state_max_night": ("int", 60, False, []),

    # Humanizer — milk
    "milk_min_day": ("int", 1, False, []),
    "milk_max_day": ("int", 30, False, []),
    "milk_min_night": ("int", 130, False, []),
    "milk_max_night": ("int", 800, False, []),
    "milk_click_min_day": ("int", 1, False, []),
    "milk_click_max_day": ("int", 4, False, []),
    "milk_click_min_night": ("int", 2, False, []),
    "milk_click_max_night": ("int", 8, False, []),
    "milk_state_min_day": ("int", 1, False, []),
    "milk_state_max_day": ("int", 30, False, []),
    "milk_state_min_night": ("int", 330, False, []),
    "milk_state_max_night": ("int", 700, False, []),

    # Humanizer — cactus
    "cactus_min_day": ("int", 1, False, []),
    "cactus_max_day": ("int", 30, False, []),
    "cactus_min_night": ("int", 30, False, []),
    "cactus_max_night": ("int", 60, False, []),
    "cactus_click_min_day": ("int", 1, False, []),
    "cactus_click_max_day": ("int", 7, False, []),
    "cactus_click_min_night": ("int", 2, False, []),
    "cactus_click_max_night": ("int", 15, False, []),
    "cactus_state_min_day": ("int", 1, False, []),
    "cactus_state_max_day": ("int", 30, False, []),
    "cactus_state_min_night": ("int", 30, False, []),
    "cactus_state_max_night": ("int", 500, False, []),

    # Humanizer — chick house
    "chick_house_min_day": ("int", 1, False, []),
    "chick_house_max_day": ("int", 300, False, []),
    "chick_house_min_night": ("int", 300, False, []),
    "chick_house_max_night": ("int", 600, False, []),
    "chick_house_click_min_day": ("int", 1, False, []),
    "chick_house_click_max_day": ("int", 5, False, []),
    "chick_house_click_min_night": ("int", 2, False, []),
    "chick_house_click_max_night": ("int", 10, False, []),
    "chick_house_state_min_day": ("int", 1, False, []),
    "chick_house_state_max_day": ("int", 300, False, []),
    "chick_house_state_min_night": ("int", 300, False, []),
    "chick_house_state_max_night": ("int", 600, False, []),

    # Прочее
    "config_access_keys": ("list[str]", [], True, []),
}

def find_hikka_dir(default: str) -> str:
    candidates = [os.getcwd(), str(Path.cwd().parent), default]
    for c in candidates:
        p = Path(c)
        if p.exists() and any(p.glob("config-*.json")):
            return c
    return default

def list_user_configs(root: str) -> List[Path]:
    return sorted(Path(root).glob("config-*.json"))

def derive_user_id_from_filename(p: Path) -> str:
    m = re.match(r"config-(\d+)\.json$", p.name)
    return m.group(1) if m else ""

def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    backup = path.with_suffix(path.suffix + f".bak.{int(time.time())}")
    shutil.copy2(path, backup)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)

def get_autofarm_config(doc: Dict[str, Any]) -> Tuple[Dict[str, Any]]:
    auto = doc.get("AutoFarmbot", {})
    cfg = auto.get("__config__", {})
    return cfg,

def set_autofarm_config(doc: Dict[str, Any], new_cfg: Dict[str, Any]) -> None:
    if "AutoFarmbot" not in doc:
        doc["AutoFarmbot"] = {}
    doc["AutoFarmbot"]["__config__"] = new_cfg

def coerce_value(type_name: str, value: Any):
    if type_name == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "y", "on")
        return bool(value)
    if type_name == "int":
        try:
            return int(value)
        except Exception:
            return 0
    if type_name == "str":
        return "" if value is None else str(value)
    if type_name == "list[str]":
        if isinstance(value, list):
            return [str(x) for x in value]
        return []
    return value

def ensure_defaults(cfg: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(cfg)
    for key, (typ, default, _multi, _choices) in FIELD_SPEC.items():
        if key not in out:
            out[key] = default
        else:
            out[key] = coerce_value(typ, out[key])
    return out

def render_field(key: str, spec: Tuple[str, Any, bool, List[str]], value: Any):
    typ, default, is_multi, choices = spec
    label = key
    if typ == "bool":
        return st.toggle(label, value=bool(value))
    if typ == "int":
        return st.number_input(label, value=int(value), step=1)
    if typ == "str":
        if choices:
            # Подсказки: просто отображаем хинт
            st.caption(f"Подсказки: {', '.join(choices)}")
        return st.text_input(label, value=str(value))
    if typ == "list[str]":
        if choices:
            # multiselect по списку
            current = [v for v in value if v in choices] if isinstance(value, list) else []
            return st.multiselect(label, options=choices, default=current)
        # иначе textarea по одному значению в строке
        raw = "\n".join([str(x) for x in (value or [])])
        edited = st.text_area(label, value=raw, height=120, help="По одному значению в строке")
        items = [line.strip() for line in edited.splitlines() if line.strip()]
        return items
    return value

UI_GROUPS: List[Tuple[str, List[str]]] = [
    ("Общие", [
        "config_user_tz",
        "config_debug_msg",
        "config_debug_diff_msg",
        "config_bot_send_logs",
        "config_bot_deletemsg_inbot",
        "config_redis_cloud_link",
        "config_access_keys",
    ]),
    ("Бот и чат", [
        "config_bot_used_bot",
        "config_bot_used_chat_id",
    ]),
    ("Еда", [
        "config_bot_auto_eat",
        "config_bot_auto_eating_forest",
        "config_bot_eat_use_count",
        "config_bot_eat_use_item",
        "config_bot_eat_lvl",
        "config_bot_auto_eat_command",
    ]),
    ("Дойка", [
        "config_bot_auto_milk",
        "config_bot_auto_milk_command",
    ]),
    ("Крафт", [
        "config_bot_auto_craft",
        "config_bot_auto_craft_count",
        "config_bot_auto_craft_item_name",
        "config_bot_auto_craft_command",
        "craft_min_day","craft_max_day","craft_min_night","craft_max_night",
        "craft_click_min_day","craft_click_max_day","craft_click_min_night","craft_click_max_night",
        "craft_state_min_day","craft_state_max_day","craft_state_min_night","craft_state_max_night",
    ]),
    ("Лес", [
        "config_bot_auto_forest",
        "config_bot_auto_forest_command",
        "config_bot_auto_forest_skip_npc",
        "config_bot_autoforest_npcs",
        "forest_min_day","forest_max_day","forest_min_night","forest_max_night",
        "forest_click_min_day","forest_click_max_day","forest_click_min_night","forest_click_max_night",
        "forest_npc_min_day","forest_npc_max_day","forest_npc_min_night","forest_npc_max_night",
        "forest_state_min_day","forest_state_max_day","forest_state_min_night","forest_state_max_night",
    ]),
    ("Скин", [
        "config_bot_skin_show",
        "config_bot_skin_strings_id",
        "config_bot_skin_strings_hash",
        "config_bot_skin_strings_bytes",
    ]),
    ("Кактус", [
        "config_bot_auto_cactus",
        "config_bot_auto_cactus_water_drink",
        "config_bot_auto_cactus_water_drink_lvl",
        "config_bot_auto_cactus_water_drink_click",
        "cactus_min_day","cactus_max_day","cactus_min_night","cactus_max_night",
        "cactus_click_min_day","cactus_click_max_day","cactus_click_min_night","cactus_click_max_night",
        "cactus_state_min_day","cactus_state_max_day","cactus_state_min_night","cactus_state_max_night",
    ]),
    ("Курятник/телята", [
        "config_bot_auto_baby_tabs",
        "config_bot_auto_chick_house_chick_count",
        "config_bot_auto_chick_house",
        "config_bot_auto_chick_house_water",
        "config_bot_auto_chick_house_gather",
        "chick_house_min_day","chick_house_max_day","chick_house_min_night","chick_house_max_night",
        "chick_house_click_min_day","chick_house_click_max_day","chick_house_click_min_night","chick_house_click_max_night",
        "chick_house_state_min_day","chick_house_state_max_day","chick_house_state_min_night","chick_house_state_max_night",
    ]),
]

def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)

    with st.sidebar:
        st.header("Источник")
        detected = find_hikka_dir(DEFAULT_HIKKA_DIR)
        hikka_dir = st.text_input("Hikka directory", value=detected)
        cfg_files = list_user_configs(hikka_dir)
        options = [p.name for p in cfg_files]
        selected_name = st.selectbox("Конфиг-файл", options) if options else None
        manual_user_id = st.text_input("user_id (если файла нет в списке)", value="")
        st.caption("Файл должен называться config-<id>.json в директории Hikka.")
        st.divider()
        st.header("Действия")
        apply_hot_reload = st.checkbox("Hot-reload (выполнить команду в Hikka вручную)", value=False)
        hot_reload_cmd = st.text_input("Команда для Hikka", value=".moofarm reloadconfig")

    if not Path(hikka_dir).exists():
        st.error(f"Директория не найдена: {hikka_dir}")
        return

    cfg_path = None
    if selected_name:
        cfg_path = Path(hikka_dir) / selected_name
    elif manual_user_id.strip():
        cfg_path = Path(hikka_dir) / f"config-{manual_user_id.strip()}.json"

    if not cfg_path or not cfg_path.exists():
        st.warning("Выберите существующий config-*.json или укажите корректный user_id.")
        if cfg_files:
            st.info("Найдены: " + ", ".join([p.name for p in cfg_files]))
        return

    st.subheader(f"Редактирование: {cfg_path.name}")
    st.caption(str(cfg_path))

    try:
        doc = load_json(cfg_path)
    except Exception as e:
        st.exception(e)
        return

    (cfg,) = get_autofarm_config(doc)
    cfg = ensure_defaults(cfg)

    # Рендер всех групп
    edited: Dict[str, Any] = {}
    for group_name, keys in UI_GROUPS:
        with st.expander(group_name, expanded=False):
            for key in keys:
                spec = FIELD_SPEC[key]
                current = cfg.get(key, spec[1])
                edited[key] = render_field(key, spec, current)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Сохранить", type="primary"):
            try:
                new_cfg = {}
                for k, (typ, default, _m, _c) in FIELD_SPEC.items():
                    new_cfg[k] = coerce_value(typ, edited.get(k, cfg.get(k, default)))
                set_autofarm_config(doc, new_cfg)
                save_json_atomic(cfg_path, doc)
                st.success("Сохранено (атомарно, создан бэкап).")
                if apply_hot_reload:
                    st.info(f"Выполните в Hikka: {hot_reload_cmd}")
            except Exception as e:
                st.exception(e)
    with col2:
        if st.button("Отменить изменения"):
            st.experimental_rerun()
    with col3:
        if st.button("Создать бэкап"):
            try:
                backup = cfg_path.with_suffix(cfg_path.suffix + f".manual.bak.{int(time.time())}")
                shutil.copy2(cfg_path, backup)
                st.success(f"Бэкап: {backup.name}")
            except Exception as e:
                st.exception(e)

    st.divider()
    st.subheader("Текущий JSON (после загрузки)")
    st.json(doc)

if __name__ == "__main__":
    main()
