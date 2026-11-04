# PHP / Nginx 管理器

Windows 桌面工具，用 PyQt6 管理多版本 PHP、本地 Nginx 站点和 hosts。

## 能做什么

- **PHP**：从 windows.php.net 下载安装任意 NTS x64 版本（可看全部可下载版本，不只最新）；带进度条、速度、剩余时间，可取消；切换当前版本；删除版本
- **依赖查看**：PHP 页「依赖与扩展」显示每个版本已启用/未启用的扩展，以及 `php -m` 实际加载的运行时模块
- **php.ini**：常用设置（内存、上传上限、时区、错误显示、OPcache 等）用下拉框改；扩展开关一键启用/停用；也可直接编辑原始文本，保存前自动备份
- **站点**：新增/编辑站点（域名、端口、目录、PHP 版本），每个站点有独立的 `data/sites/<名>/site.conf` 配置片段可单独编辑，主配置只 include 这些片段
- **Nginx**：从 nginx.org 下载安装一个 Windows 版到 `data/nginx/`；启动/停止/重载/测试配置
- **hosts**：在系统 hosts 里维护一段本工具的域名记录
- **多版本共存**：每个 PHP 版本各占一个 fastcgi 端口（8.3.x → 9803、8.4.x → 9804…），同版本的多个站点共用一个 php-cgi 进程，不同版本互不干扰
- 站点页可单独**启动 / 重启 / 停止 php-cgi**，改完站点配置后重载 Nginx 会自动对齐 php-cgi（换版本时旧进程自动退出）

## 新增站点时会发生什么

- 域名默认跟随站点名：站点叫 `demo` → 域名 `demo.local`，端口默认 **80**（被占用时自动找下一个空闲端口）
- 想用 IP 就勾上「用 IP（127.0.0.1）代替域名」，不写 hosts
- 域名是 `.local` / `.localhost` 这类本地域名时，保存前会检查系统 hosts：没有就自动写一条 `127.0.0.1 <域名>`；已有就不动（写 hosts 需要管理员权限，失败会提示但不影响建站）
- 站点列表上的**打开**按钮用默认浏览器访问 `http://<域名>:<端口>/`

## 运行

```powershell
pip install -r requirements.txt
python gui/main.py
```

改 hosts 需要管理员权限，否则写入会失败。

## 目录

```text
config/config.yaml   配置（PHP 版本列表、cgi 端口分配、Nginx 数据路径、hosts 标记）
data/versions/       已安装的 PHP（每版本一个目录）
data/nginx/          Nginx 安装目录（conf、logs）
data/sites/<名>/     每站点：site.json（元数据）+ site.conf（nginx 配置片段）
data/www/            默认网站目录
```

## 说明

- 每个 PHP 版本一个 fastcgi 端口，默认 `9000 + 主版本*100 + 次版本`（8.3.36 → 9803、8.4.27 → 9804）；分配结果记在 `config.yaml` 的 `php.cgi_ports` 里，同一版本始终用同一个端口
- 站点的 `fastcgi_pass` 写在 `site.conf` 里；Nginx 启动/重载前会重写主配置，但不会动各站点的片段，手改的片段内容安全
- php.ini / hosts 写入前都会在同目录留 `*.bak-时间戳` 备份
- hosts 里由本工具写入的记录都在 `# BEGIN php-server` / `# END php-server` 标记段内，删除站点时对应的 `.local` 记录会一并清掉

## 测试

```powershell
pip install pytest
python -m pytest tests/ -q
```

测试用临时目录，不会碰你的 `data/` 和 `config.yaml`；GUI 测试跑在 Qt 的 offscreen 模式下，不会弹窗。
