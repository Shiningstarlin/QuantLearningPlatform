# 生产部署说明

建议把前端和后端拆成两个容器：

- 后端容器运行 FastAPI，只负责 API、数据库、行情刷新和模拟任务。
- 前端容器先构建 React 静态文件，再由 Nginx 提供页面，并把浏览器访问的 `/api` 转发到后端容器。

这样浏览器只需要访问一个站点地址，后端也可以独立重启或扩容。

## 服务器首次准备

1. 拉取代码。
2. 复制并编辑生产环境变量：

```bash
cp backend/.env.production.example backend/.env.production
```

3. 启动：

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

4. 查看服务状态：

```bash
docker compose -f docker-compose.prod.yml ps
```

## 必须编辑的文件

`backend/.env.production` 需要按服务器实际情况修改：

- `SECRET_KEY`：生产登录密钥，必须换成足够长的随机字符串。
- `DATABASE_URL`：生产库应使用 `quant_prod`；密码中的 `@` 要写成 `%40`。
- `FRONTEND_ORIGIN`：正式域名，例如 `https://quant.example.com`；如果只用服务器 IP 临时访问，可先写 `http://服务器IP`。
- `FUTU_HOST` / `FUTU_PORT`：FutuOpenD 的地址。如果 FutuOpenD 跑在 Docker 宿主机，Linux Docker 常用 `host.docker.internal:11111`，本项目 compose 已加 `host-gateway` 映射。
- `YFINANCE_PROXY_URL`：生产环境如果也需要代理访问 Yahoo Finance，在这里填写服务器可访问的代理地址。

`docker-compose.prod.yml` 通常只需要改：

- `frontend.ports`：默认把容器 80 端口映射到服务器 80。
- 如果你的服务器已有 Nginx/Caddy 负责 HTTPS，可以把前端端口改成内网端口，例如 `"8080:80"`，再由外层反向代理转发。

## 邀请码

生产库第一次启动后，如果需要生成邀请码：

```bash
docker compose -f docker-compose.prod.yml exec backend python -m app.scripts.generate_invitation_codes --count 10
```

生成的码会输出在终端，并写入当前 `DATABASE_URL` 指向的数据库。
