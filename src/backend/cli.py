import click


@click.group()
def main():
    pass


@main.group(help="数据管理")
def data():
    pass


@data.command(help="初始化数据")
def init_db():
    from app.utils.init_db import init_all

    init_all()


@data.command(help="创建超级管理员账户，已存在则直接提升权限")
@click.option("--email", prompt=True, type=str, help="邮箱", required=True)
@click.option("--password", prompt=True, type=str, help="密码，至少8位", required=True)
def create_superuser(email, password):
    from app.utils.init_db import create_superuser as create_superuser_

    create_superuser_(email=email, password=password)


@data.command(help="为缺失默认模型配置的历史用户补齐一行配置")
def backfill_default_model():
    from app.utils.init_db import backfill_user_default_models

    backfill_user_default_models()


@main.group(help="服务管理")
def server():
    pass


@server.command(help="预启动")
def pre_start():
    from app.backend_pre_start import pre_start as backend_pre_start

    backend_pre_start()


if __name__ == "__main__":
    main()
