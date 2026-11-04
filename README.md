# PHP / Nginx 管理器

Windows 桌面工具，用 PyQt6 管理多版本 PHP、本地 Nginx 站点和 hosts。

## 能做什么

- 安装各主版本最新的 PHP（NTS x64），7.4 与 8.x 可同时存在
- 切换当前版本，编辑对应的 `php.ini`（保存前自动备份）
- 添加本地站点，生成 Nginx 配置
- 在系统 hosts 里维护一段本工具的域名记录

## 运行

```powershell
pip install -r requirements.txt
python gui/main.py
```

PHP 安装包从 windows.php.net 下载，解压到 `data/versions/<版本>/`。

Nginx 需要自行放到 `data/nginx/nginx.exe`（官方 Windows 包解压后的内容），或保证 `nginx` 已在 PATH 中。改 hosts 需要管理员权限，否则写入会失败。

站点的 PHP 请求走 `127.0.0.1:9000+端口余数` 的 php-cgi。当前版本会写出 Nginx 的 fastcgi 配置，启动 php-cgi 进程尚未接上，站点页的「启动 Nginx」只拉起 Nginx。
