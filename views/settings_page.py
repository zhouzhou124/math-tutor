"""pages/settings_page.py — 系统设置"""
import streamlit as st
import os
import time
from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from llm_client import create_client
import credential_store

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # views/ parent


def render_settings_page(db, render_latex):
    """..."""
    st.title("⚙️ 系统设置")

    # ── 加载已有 profiles ──
    profiles = credential_store.load_profiles()
    profile_names = [p["name"] for p in profiles]
    active = credential_store.get_active_profile()

    # ═══════════════════════════════════════
    #  Provider 配置管理
    # ═══════════════════════════════════════
    with st.container(border=True):
        st.subheader("🔑 LLM Provider 管理")
        st.caption("支持多个大模型配置，一键切换。API Key 自动加密保存 15 天，过期自动清除。")

        # ── 已有配置列表 ──
        if profiles:
            st.markdown("**已保存的配置：**")
            for p in profiles:
                is_active = active and p["name"] == active["name"]
                badge = "🟢 使用中" if is_active else "⚪"
                proto_label = p.get("protocol", "openai")
                col_name, col_info, col_act, col_del = st.columns([2, 3, 1, 1])
                with col_name:
                    st.markdown(f"**{p['name']}** {badge}")
                with col_info:
                    masked = credential_store.mask_key(p.get("api_key", ""))
                    days_left = p.get("ttl_days", 15) - int((time.time() - p.get("created_at", 0)) / 86400)
                    st.caption(f"{p.get('base_url', '')} | {p.get('model', '')} | {proto_label} | Key: {masked} | {max(0, days_left)}天后过期")
                with col_act:
                    if not is_active:
                        if st.button("切换", key=f"switch_{p['name']}"):
                            credential_store.set_active_profile(p["name"])
                            st.session_state.api_key = p["api_key"]
                            st.session_state.base_url = p["base_url"]
                            st.session_state.model = p["model"]
                            st.session_state.protocol = p.get("protocol", "openai")
                            st.session_state.llm_client = create_client(
                                api_key=p["api_key"],
                                base_url=p["base_url"],
                                protocol=p.get("protocol", "openai"),
                            )
                            st.toast(f"已切换到 {p['name']}")
                            st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{p['name']}", help=f"删除 {p['name']}"):
                        credential_store.delete_profile(p["name"])
                        st.toast(f"已删除 {p['name']}")
                        st.rerun()
            st.markdown("---")

        # ── 新增/编辑配置（简化版）──
        st.markdown("**添加配置：**")

        # 预设: (base_url, model, protocol)
        presets = {
            "DeepSeek": ("https://api.deepseek.com/anthropic", "deepseek-v4-pro", "anthropic"),
            "OpenAI": ("https://api.openai.com/v1", "gpt-4o", "openai"),
            "通义千问": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus", "openai"),
            "Kimi": ("https://api.moonshot.cn/v1", "moonshot-v1-8k", "openai"),
            "智谱": ("https://open.bigmodel.cn/api/paas/v4", "glm-4", "openai"),
        }

        preset = st.selectbox(
            "选择服务商",
            list(presets.keys()),
            key="provider_preset",
        )
        default_url, default_model, default_protocol = presets[preset]

        profile_key = st.text_input(
            "API Key",
            type="password",
            placeholder="粘贴你的 API Key",
            key="profile_key_input",
        )

        # 高级选项：URL、模型名、协议，默认折叠
        with st.expander("高级选项（通常无需修改）"):
            profile_url = st.text_input(
                "API Base URL", value=default_url, key="profile_url_input",
            )
            profile_model = st.text_input(
                "模型名称", value=default_model, key="profile_model_input",
            )
            profile_protocol = st.selectbox(
                "API 协议",
                ["openai", "anthropic"],
                index=0 if default_protocol == "openai" else 1,
                key="profile_protocol_input",
                help="OpenAI 兼容接口选 openai，Anthropic 接口选 anthropic",
            )

        save_col, test_col = st.columns(2)
        with save_col:
            if st.button("💾 保存并启用", type="primary", use_container_width=True,
                         disabled=not profile_key):
                credential_store.save_profile(
                    name=preset,
                    api_key=profile_key,
                    base_url=profile_url or default_url,
                    model=profile_model or default_model,
                    ttl_days=15,
                    protocol=profile_protocol,
                )
                st.session_state.api_key = profile_key
                st.session_state.base_url = profile_url or default_url
                st.session_state.model = profile_model or default_model
                st.session_state.protocol = profile_protocol
                st.session_state.llm_client = create_client(
                    api_key=profile_key,
                    base_url=profile_url or default_url,
                    protocol=profile_protocol,
                )
                st.success(f"✅ {preset} 已保存并启用（协议: {profile_protocol}）")
                st.rerun()

        with test_col:
            if st.button("🔍 测试连接", use_container_width=True,
                         disabled=not profile_key):
                try:
                    test_client = create_client(
                        api_key=profile_key,
                        base_url=profile_url or default_url,
                        protocol=profile_protocol,
                    )
                    resp = test_client.chat.completions.create(
                        model=profile_model or default_model,
                        messages=[{"role": "user", "content": "说一个数字"}],
                        max_tokens=10,
                    )
                    st.success(f"✅ 连接成功: {resp.choices[0].message.content}")
                except Exception as e:
                    st.error(f"❌ 连接失败: {e}")

    # ═══════════════════════════════════════
    #  当前生效配置一览
    # ═══════════════════════════════════════
    with st.container(border=True):
        st.subheader("📋 当前生效配置")
        if active:
            ic1, ic2, ic3, ic4, ic5 = st.columns(5)
            ic1.metric("配置名称", active["name"])
            ic2.metric("Base URL", active.get("base_url", "-"))
            ic3.metric("模型", active.get("model", "-"))
            ic4.metric("协议", active.get("protocol", "openai"))
            days_left = active.get("ttl_days", 15) - int((time.time() - active.get("created_at", 0)) / 86400)
            ic5.metric("剩余天数", f"{max(0, days_left)} 天")
        else:
            st.info("尚未配置 API Key，请在上方添加 Provider 配置。")

    # ═══════════════════════════════════════
    #  隐私安全检查
    # ═══════════════════════════════════════
    with st.container(border=True):
        st.subheader("🔒 隐私安全检查")
        st.caption("扫描项目文件，检测可能泄露的 API Key / Secret")

        if st.button("🔍 扫描隐私泄露风险", use_container_width=True):
            import re as _re
            sensitive_patterns = [
                (r'sk-[a-zA-Z0-9]{20,}', '疑似 OpenAI/DeepSeek API Key'),
                (r'api_key\s*=\s*["\'][a-zA-Z0-9]{16,}["\']', '硬编码的 API Key'),
                (r'password\s*=\s*["\'][^"\']{4,}["\']', '硬编码的密码'),
                (r'token\s*=\s*["\'][a-zA-Z0-9]{16,}["\']', '硬编码的 Token'),
            ]
            scan_dirs = ["agents", "prompts", "storage/questions"]
            scan_exts = {".py", ".json", ".md", ".yaml", ".yml"}
            findings = []

            for scan_dir in scan_dirs:
                full_dir = os.path.join(_ROOT, scan_dir)
                if not os.path.isdir(full_dir):
                    continue
                for root, _, files in os.walk(full_dir):
                    for fname in files:
                        if os.path.splitext(fname)[1] not in scan_exts:
                            continue
                        fpath = os.path.join(root, fname)
                        try:
                            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                            for pattern, desc in sensitive_patterns:
                                for m in _re.finditer(pattern, content):
                                    findings.append((fpath, desc, m.group()[:20] + "..."))
                        except Exception:
                            pass

            # 也扫描根目录 py 文件
            for fname in os.listdir(_ROOT):
                if fname.endswith(".py"):
                    fpath = os.path.join(_ROOT, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        for pattern, desc in sensitive_patterns:
                            for m in _re.finditer(pattern, content):
                                findings.append((fpath, desc, m.group()[:20] + "..."))
                    except Exception:
                        pass

            if findings:
                st.warning(f"⚠️ 发现 {len(findings)} 处潜在泄露风险：")
                for fpath, desc, snippet in findings[:20]:
                    rel = os.path.relpath(fpath, _ROOT)
                    st.caption(f"  `{rel}` — {desc}: `{snippet}`")
            else:
                st.success("✅ 未发现明显的 API Key 泄露风险")

        # .gitignore 状态
        st.markdown("**`.gitignore` 敏感文件覆盖检查：**")
        gitignore_path = os.path.join(_ROOT, ".gitignore")
        critical_files = [".env", ".env.*", "storage/.credentials.json", "storage/settings.json"]
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8") as f:
                gi_content = f.read()
            for cf in critical_files:
                if cf in gi_content:
                    st.caption(f"✅ `{cf}` — 已被 .gitignore 排除")
                else:
                    st.error(f"❌ `{cf}` — 未被 .gitignore 排除，有泄露风险！")
        else:
            st.error("❌ 项目根目录缺少 .gitignore 文件")

    # ═══════════════════════════════════════
    #  数据管理
    # ═══════════════════════════════════════
    with st.container(border=True):
        # ── Mathpix OCR 配置 ──
        st.markdown("---")
        st.subheader("🔢 数学公式 OCR（Mathpix）")
        st.caption("Mathpix 是专业数学公式识别服务，支持手写和印刷体。注册获取 API Key：https://mathpix.com")

        from vision.mathpix_client import is_available as _mp_avail, get_mathpix_credentials as _mp_cred
        _mp_id, _mp_key = _mp_cred()
        _mp_configured = bool(_mp_id and _mp_key)

        if _mp_configured:
            st.success(f"✅ Mathpix 已配置（App ID: {_mp_id[:8]}...）")
        else:
            st.info("ℹ️ Mathpix 未配置，OCR 将使用本地引擎（准确率较低）")

        mp_col1, mp_col2 = st.columns(2)
        with mp_col1:
            new_mp_id = st.text_input(
                "Mathpix App ID",
                value=_mp_id or "",
                type="default",
                placeholder="输入 Mathpix App ID",
                key="mathpix_app_id_input",
            )
        with mp_col2:
            new_mp_key = st.text_input(
                "Mathpix App Key",
                value=_mp_key or "",
                type="password",
                placeholder="输入 Mathpix App Key",
                key="mathpix_app_key_input",
            )

        if st.button("💾 保存 Mathpix 配置", type="primary", use_container_width=True,
                     disabled=not (new_mp_id and new_mp_key)):
            import json
            settings_path = "storage/settings.json"
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            except Exception:
                settings = {}
            settings["mathpix_app_id"] = new_mp_id
            settings["mathpix_app_key"] = new_mp_key
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            st.session_state.mathpix_app_id = new_mp_id
            st.session_state.mathpix_app_key = new_mp_key
            st.success("✅ Mathpix 配置已保存！")
            st.rerun()

        st.subheader("数据管理")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ 清空错题本", type="secondary"):
                st.session_state.memory.clear_all()
                st.warning("错题本和画像已重置")
                st.rerun()
        with col2:
            st.caption(f"错题数: {st.session_state.memory.get_error_stats(st.session_state.auth['user_id']).total_errors}")
            st.caption(f"数据位置: `E:\\math_tutor\\storage\\`")

