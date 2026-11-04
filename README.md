# PHP / Nginx 管理器

Windows 桌面工具，用 PyQt6 管理多版本 PHP、本地 Nginx 站点和 hosts。

## 能做什么

- **PHP**：从 windows.php.net 下载安装任意 NTS x64 版本（可看全部可下载版本，不只最新）；带进度条、速度、剩余时间，可取消；切换当前版本；删除版本
- **依赖查看**：PHP 页「依赖与扩展」显示每个版本已启用/未启用的扩展，以及 `php -m` 实际加载的运行时模块
- **php.ini**：常用设置（内存、上传上限、时区、错误显示、OPcache 等）用下拉框改；扩展开关一键启用/停用；也可直接编辑原始文本，保存前自动备份
- **站点**：新增/编辑站点（域名、端口、目录、PHP 版本），每个站点有独立的 `data/sites/<名>/site.conf` 配置片段可单独编辑，主配置只 include 这些片段
- **Nginx**：从 nginx.org 下载安装一个 Windows 版到 `data/nginx/`；启动/停止/重载/测试配置
- **hosts**：在系统 hosts 里维护一段本工具的域名记录
- 站点页「启动 Nginx」会同时按站点配置拉起各站点的 php-cgi（`127.0.0.1:<fastcgi 端口>`）

## 运行

```powershell
pip install -r requirements.txt
python gui/main.py
```

改 hosts 需要管理员权限，否则写入会失败。

## 目录

```text
config/config.yaml   配置（PHP 版本列表、Nginx 数据路径、hosts 标记）
data/versions/       已安装的 PHP（每版本一个目录）
data/nginx/          Nginx 安装目录（conf、logs）
data/sites/<名>/     每站点：site.json（元数据）+ site.conf（nginx 配置片段）
data/www/            默认网站目录
```

## 说明

- 站点的 php-cgi 端口 = `9000 + (站点端口 % 1000)`，写在 `site.conf` 的 `fastcgi_pass` 里；Nginx 启动前会重写主配置，但不会动各站点的片段，手改的片段内容安全
- php.ini / hosts 写入前都会在同目录留 `*.bak-时间戳` 备份
