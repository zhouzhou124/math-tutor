# Streamlit Community Cloud 部署说明
# ====================================
# 
# 方式一：Streamlit Community Cloud（免费，推荐）
# -------------------------------------------
# 1. 将项目推送到 GitHub 公开仓库：
#      git init && git add -A && git commit -m "init"
#      git remote add origin https://github.com/YOUR_USER/math-tutor.git
#      git push -u origin main
#
# 2. 打开 https://share.streamlit.io ，用 GitHub 账号登录
# 3. 点击 "New app"，选择你的仓库、分支和 app.py
# 4. 在 Advanced settings 中填入 Secrets（API Key 等）
# 5. 点击 Deploy，等待 2-3 分钟
# 6. 部署完成后，手机上打开分配的 URL（如 https://xxx.streamlit.app）
# 7. 手机浏览器菜单 → "添加到主屏幕" → 桌面图标像原生 App
#
# 注意：Streamlit Cloud 免费版有资源限制（1GB RAM），且文件系统不持久
#
# 方式二： Docker 部署（自己服务器 / VPS）
# -------------------------------------------
# docker build -t math-tutor .
# docker run -d -p 8501:8501 --name math-tutor math-tutor
#
# 方式三： 手机访问局域网（家里/自习室，PC 需开机）
# -------------------------------------------
# 1. 电脑双击 setup_firewall.bat（只需一次，需管理员）
# 2. 双击 start_hidden.vbs 或 run.bat 启动服务
# 3. 查电脑局域网 IP（PowerShell）:
#      ipconfig
#    找到「无线局域网适配器」下的 IPv4，例如 192.168.1.100
# 4. 手机连同一 WiFi，浏览器打开:
#      http://192.168.1.100:8501
# 5. 浏览器菜单 →「添加到主屏幕」→ 桌面图标（类似 App）
#
# 局限：电脑关机或离开该 WiFi 后无法访问；不算「随时随地」。
#
# 方式四： 随时随地（需公网部署）
# -------------------------------------------
# 用方式一 Streamlit Cloud，或方式二 云服务器 Docker。
# API Key 在部署平台的 Secrets / 环境变量中配置。
# 注意：云端文件系统可能不持久，题库/错题数据需另行备份或接数据库。
