# 设计文档：CLI 数据库运维工具

## 概述

CLI 数据库运维工具为 OwlClaw 提供统一的数据库运维命令行接口。该工具基于 Typer 框架构建，封装了 Alembic API、pg_dump、pg_restore 等底层工具，提供一致的用户体验。

核心功能包括：

- **数据库初始化**：在宿主 PostgreSQL 上创建 database、role 和 extension
- **Schema 迁移**：执行和管理 Alembic 迁移
- **状态检查**：查看数据库连接、迁移版本、表统计等信息
- **备份恢复**：使用 pg_dump/pg_restore 进行数据备份和恢复
- **健康检查**：检查连接池、慢查询、磁盘使用等指标

设计遵循以下原则：

1. **使用成熟框架**：基于 Typer 构建，Typer 是 FastAPI 作者开发的现代 CLI 框架，提供自动帮助生成、参数验证、类型检查等功能
2. **封装底层工具**：不直接调用命令行工具，而是使用 Python API（Alembic API、asyncpg 等）
3. **统一用户体验**：所有命令提供一致的参数格式和错误处理
4. **清晰的错误消息**：提供可操作的错误提示和解决建议
5. **支持 dry-run**：允许用户预览操作而不实际执行
6. **灵活的配置**：支持环境变量、配置文件和命令行参数

### 技术栈选择

**CLI 框架：Typer**

Typer 是一个现代的 Python CLI 框架，提供以下优势：

- **自动帮助生成**：从函数签名和文档字符串自动生成帮助文本
- **类型检查**：基于 Python 类型注解自动验证参数
- **参数解析**：自动处理选项、参数、标志等
- **子命令支持**：原生支持命令组和子命令
- **测试支持**：提供 CliRunner 用于测试
- **零学习成本**：如果熟悉 FastAPI，Typer 的 API 非常相似

**输出美化：Rich**

Rich 是一个 Python 库，用于在终端中创建丰富的文本和美观的格式：

- **颜色和样式**：支持颜色、粗体、斜体等
- **表格**：创建美观的表格
- **进度条**：显示进度指示器和旋转器
- **语法高亮**：支持代码和 SQL 语法高亮

**数据库操作：**

- **Alembic**：用于 schema 迁移（已在 database-core spec 中选择）
- **asyncpg**：异步 PostgreSQL 驱动（已在 database-core spec 中选择）
- **SQLAlchemy**：ORM 和查询构建（已在 database-core spec 中选择）

**外部工具：**

- **pg_dump**：PostgreSQL 官方备份工具（需要用户安装 PostgreSQL 客户端）
- **pg_restore**：PostgreSQL 官方恢复工具（需要用户安装 PostgreSQL 客户端）

这些工具都是成熟的、经过生产验证的解决方案，可以大大减少我们需要从头实现的代码量。

## 架构

### 模块结构

```
owlclaw/
└── cli/
    ├── __init__.py          # CLI 主入口
    ├── db.py                # db 子命令组
    ├── db_init.py           # init 命令实现
    ├── db_migrate.py        # migrate 命令实现
    ├── db_status.py         # status 命令实现
    ├── db_revision.py       # revision 命令实现
    ├── db_rollback.py       # rollback 命令实现
    ├── db_backup.py         # backup 命令实现
    ├── db_restore.py        # restore 命令实现
    ├── db_check.py          # check 命令实现
    ├── config.py            # 配置读取
    ├── output.py            # 输出格式化和进度显示
    └── exceptions.py        # CLI 异常类
```


### 依赖关系

```mermaid
graph TD
    A[owlclaw.cli:main] --> B[db.py]
    B --> C[db_init.py]
    B --> D[db_migrate.py]
    B --> E[db_status.py]
    B --> F[db_revision.py]
    B --> G[db_rollback.py]
    B --> H[db_backup.py]
    B --> I[db_restore.py]
    B --> J[db_check.py]
    
    C --> K[config.py]
    D --> K
    E --> K
    F --> K
    G --> K
    H --> K
    I --> K
    J --> K
    
    C --> L[output.py]
    D --> L
    E --> L
    F --> L
    G --> L
    H --> L
    I --> L
    J --> L
    
    D --> M[Alembic API]
    F --> M
    G --> M
    
    C --> N[SQLAlchemy]
    E --> N
    J --> N
    
    H --> O[subprocess: pg_dump]
    I --> P[subprocess: pg_restore]
```

### 数据流

```mermaid
sequenceDiagram
    participant User as 用户
    participant CLI as CLI 入口
    participant Config as 配置读取
    participant Command as 命令实现
    participant Tool as 底层工具
    participant DB as PostgreSQL
    
    User->>CLI: owlclaw db migrate
    CLI->>Config: 读取配置
    Config->>Config: 环境变量 > 配置文件
    Config->>CLI: Database_URL
    CLI->>Command: 执行 migrate
    Command->>Tool: Alembic API
    Tool->>DB: 执行 SQL
    DB->>Tool: 结果
    Tool->>Command: 迁移完成
    Command->>CLI: 格式化输出
    CLI->>User: 显示结果
```

## 组件和接口

### 1. CLI 主入口 (__init__.py)

**职责**：
- 定义 CLI 应用入口
- 注册子命令组

**接口**：

```python
import typer

app = typer.Typer(
    name="owlclaw",
    help="OwlClaw CLI - Agent framework for business applications",
    no_args_is_help=True,
)

def main() -> None:
    """CLI 主入口函数"""
    app()
```


### 2. DB 子命令组 (db.py)

**职责**：
- 定义 db 子命令组
- 注册所有 db 相关命令

**接口**：

```python
import typer
from owlclaw.cli.db_init import init_command
from owlclaw.cli.db_migrate import migrate_command
from owlclaw.cli.db_status import status_command
from owlclaw.cli.db_revision import revision_command
from owlclaw.cli.db_rollback import rollback_command
from owlclaw.cli.db_backup import backup_command
from owlclaw.cli.db_restore import restore_command
from owlclaw.cli.db_check import check_command

db_app = typer.Typer(
    name="db",
    help="数据库运维工具",
    no_args_is_help=True,
)

# 注册命令
db_app.command("init")(init_command)
db_app.command("migrate")(migrate_command)
db_app.command("status")(status_command)
db_app.command("revision")(revision_command)
db_app.command("rollback")(rollback_command)
db_app.command("backup")(backup_command)
db_app.command("restore")(restore_command)
db_app.command("check")(check_command)
```

### 3. 配置读取 (config.py)

**职责**：
- 从环境变量、配置文件读取数据库连接信息
- 提供配置优先级处理
- 验证配置有效性

**接口**：

```python
from typing import Optional
from pathlib import Path
import os
import yaml

class DatabaseConfig:
    """数据库配置类"""
    
    def __init__(
        self,
        url: Optional[str] = None,
        pool_size: int = 20,
        max_overflow: int = 10,
        pool_timeout: float = 30.0,
        pool_recycle: int = 1800,
        echo: bool = False,
    ):
        self.url = url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo

def get_database_url(
    cli_url: Optional[str] = None,
    config_file: Optional[Path] = None,
) -> str:
    """
    获取数据库连接 URL。
    
    优先级：CLI 参数 > 环境变量 > 配置文件
    
    Args:
        cli_url: 命令行提供的 URL
        config_file: 配置文件路径
    
    Returns:
        数据库连接 URL
    
    Raises:
        ValueError: 未找到有效的数据库 URL
    """
    # 1. CLI 参数优先级最高
    if cli_url:
        return cli_url
    
    # 2. 环境变量
    env_url = os.getenv("OWLCLAW_DATABASE_URL")
    if env_url:
        return env_url
    
    # 3. 配置文件
    if config_file and config_file.exists():
        with open(config_file) as f:
            config = yaml.safe_load(f)
            if config and "database" in config and "url" in config["database"]:
                return config["database"]["url"]
    
    raise ValueError(
        "未找到数据库连接配置。请设置 OWLCLAW_DATABASE_URL 环境变量，"
        "或在配置文件中指定 database.url，"
        "或使用 --database-url 参数。"
    )

def load_database_config(
    cli_url: Optional[str] = None,
    config_file: Optional[Path] = None,
) -> DatabaseConfig:
    """
    加载完整的数据库配置。
    
    Args:
        cli_url: 命令行提供的 URL
        config_file: 配置文件路径
    
    Returns:
        DatabaseConfig 实例
    """
    url = get_database_url(cli_url, config_file)
    
    # 从配置文件读取其他参数
    config_dict = {}
    if config_file and config_file.exists():
        with open(config_file) as f:
            config = yaml.safe_load(f)
            if config and "database" in config:
                config_dict = config["database"]
    
    return DatabaseConfig(
        url=url,
        pool_size=config_dict.get("pool_size", 20),
        max_overflow=config_dict.get("max_overflow", 10),
        pool_timeout=config_dict.get("pool_timeout", 30.0),
        pool_recycle=config_dict.get("pool_recycle", 1800),
        echo=config_dict.get("echo", False),
    )

def validate_database_url(url: str) -> None:
    """
    验证数据库 URL 格式。
    
    Args:
        url: 数据库连接 URL
    
    Raises:
        ValueError: URL 格式无效
    """
    if not url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        raise ValueError(
            f"无效的数据库 URL 格式：{url}\n"
            "期望格式：postgresql://user:pass@host:port/dbname\n"
            "或：postgresql+asyncpg://user:pass@host:port/dbname"
        )
```


### 4. 输出格式化 (output.py)

**职责**：
- 格式化命令输出
- 显示进度指示器
- 提供一致的错误消息格式

**接口**：

```python
from typing import Optional, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from contextlib import contextmanager

console = Console()

def print_success(message: str) -> None:
    """打印成功消息"""
    console.print(f"[green]✓[/green] {message}")

def print_error(message: str) -> None:
    """打印错误消息"""
    console.print(f"[red]✗[/red] {message}", err=True)

def print_warning(message: str) -> None:
    """打印警告消息"""
    console.print(f"[yellow]⚠[/yellow] {message}")

def print_info(message: str) -> None:
    """打印信息消息"""
    console.print(f"[blue]ℹ[/blue] {message}")

@contextmanager
def progress_spinner(message: str):
    """显示进度旋转器"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(message, total=None)
        try:
            yield progress
        finally:
            progress.stop()

def print_table(title: str, rows: list[dict[str, Any]], columns: list[str]) -> None:
    """打印表格"""
    table = Table(title=title)
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*[str(row.get(col, "")) for col in columns])
    console.print(table)

def confirm(message: str, default: bool = False) -> bool:
    """
    询问用户确认。
    
    Args:
        message: 确认消息
        default: 默认值
    
    Returns:
        用户是否确认
    """
    suffix = " [Y/n]" if default else " [y/N]"
    response = console.input(f"{message}{suffix}: ").strip().lower()
    
    if not response:
        return default
    
    return response in ("y", "yes")

def format_size(bytes: int) -> str:
    """格式化字节大小"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} PB"

def mask_password(url: str) -> str:
    """隐藏 URL 中的密码"""
    import re
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url)
```


### 5. 异常处理 (exceptions.py)

**职责**：
- 定义 CLI 特定的异常类
- 提供异常到用户消息的转换

**接口**：

```python
class CLIError(Exception):
    """CLI 基础异常"""
    pass

class ConfigurationError(CLIError):
    """配置错误"""
    pass

class DatabaseConnectionError(CLIError):
    """数据库连接错误"""
    def __init__(self, host: str, port: int, message: str):
        self.host = host
        self.port = port
        super().__init__(f"无法连接到 {host}:{port} - {message}")

class MigrationError(CLIError):
    """迁移错误"""
    pass

class BackupError(CLIError):
    """备份错误"""
    pass

class RestoreError(CLIError):
    """恢复错误"""
    pass

def handle_exception(e: Exception) -> int:
    """
    处理异常并返回退出码。
    
    Args:
        e: 异常对象
    
    Returns:
        退出码（非零表示错误）
    """
    from owlclaw.cli.output import print_error
    
    if isinstance(e, CLIError):
        print_error(str(e))
        return 1
    elif isinstance(e, KeyboardInterrupt):
        print_error("操作已取消")
        return 130
    else:
        print_error(f"未预期的错误：{e}")
        import traceback
        traceback.print_exc()
        return 1
```

### 6. Init 命令 (db_init.py)

**职责**：
- 在宿主 PostgreSQL 上创建 database 和 role
- 启用 pgvector 扩展
- 支持 dry-run 模式

**接口**：

```python
import typer
from typing import Optional
from owlclaw.cli.config import validate_database_url
from owlclaw.cli.output import (
    print_success, print_error, print_warning, print_info,
    progress_spinner, confirm
)
from owlclaw.cli.exceptions import DatabaseConnectionError, ConfigurationError
import asyncpg
import secrets

def init_command(
    admin_url: str = typer.Option(
        ...,
        "--admin-url",
        help="PostgreSQL 超级用户连接 URL",
    ),
    owlclaw_password: Optional[str] = typer.Option(
        None,
        "--owlclaw-password",
        help="owlclaw role 的密码（未指定则自动生成）",
    ),
    hatchet_password: Optional[str] = typer.Option(
        None,
        "--hatchet-password",
        help="hatchet role 的密码（未指定则自动生成）",
    ),
    skip_hatchet: bool = typer.Option(
        False,
        "--skip-hatchet",
        help="跳过 hatchet database 创建",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="显示将要执行的操作但不实际执行",
    ),
) -> None:
    """
    初始化 OwlClaw 数据库。
    
    在宿主 PostgreSQL 实例上创建：
    - owlclaw database 和 role
    - hatchet database 和 role（可选）
    - pgvector 扩展
    """
    try:
        validate_database_url(admin_url)
        
        # 生成密码
        if not owlclaw_password:
            owlclaw_password = secrets.token_urlsafe(32)
            print_info(f"自动生成 owlclaw 密码：{owlclaw_password}")
        
        if not skip_hatchet and not hatchet_password:
            hatchet_password = secrets.token_urlsafe(32)
            print_info(f"自动生成 hatchet 密码：{hatchet_password}")
        
        # 构建 SQL 语句
        sql_statements = _build_init_sql(
            owlclaw_password=owlclaw_password,
            hatchet_password=hatchet_password,
            skip_hatchet=skip_hatchet,
        )
        
        if dry_run:
            print_info("Dry-run 模式，将要执行的 SQL：")
            for sql in sql_statements:
                print(sql)
            return
        
        # 执行初始化
        with progress_spinner("正在初始化数据库..."):
            _execute_init_sql(admin_url, sql_statements)
        
        print_success("数据库初始化完成")
        print_info(f"owlclaw database URL: postgresql://owlclaw:{owlclaw_password}@<host>:<port>/owlclaw")
        if not skip_hatchet:
            print_info(f"hatchet database URL: postgresql://hatchet:{hatchet_password}@<host>:<port>/hatchet")
        
    except Exception as e:
        from owlclaw.cli.exceptions import handle_exception
        raise typer.Exit(handle_exception(e))

def _build_init_sql(
    owlclaw_password: str,
    hatchet_password: Optional[str],
    skip_hatchet: bool,
) -> list[str]:
    """构建初始化 SQL 语句"""
    statements = []
    
    # OwlClaw database 和 role
    statements.extend([
        f"CREATE ROLE owlclaw WITH LOGIN PASSWORD '{owlclaw_password}';",
        "CREATE DATABASE owlclaw OWNER owlclaw;",
    ])
    
    # Hatchet database 和 role
    if not skip_hatchet:
        statements.extend([
            f"CREATE ROLE hatchet WITH LOGIN PASSWORD '{hatchet_password}';",
            "CREATE DATABASE hatchet OWNER hatchet;",
        ])
    
    # pgvector 扩展（需要切换到 owlclaw database）
    statements.append("-- 切换到 owlclaw database 启用 pgvector")
    statements.append("CREATE EXTENSION IF NOT EXISTS vector;")
    
    return statements

async def _execute_init_sql(admin_url: str, statements: list[str]) -> None:
    """执行初始化 SQL"""
    # 连接到 postgres database（默认管理数据库）
    conn = await asyncpg.connect(admin_url)
    try:
        # 执行 database 和 role 创建
        for stmt in statements:
            if stmt.startswith("--"):
                continue
            if "CREATE EXTENSION" in stmt:
                break
            await conn.execute(stmt)
        
        # 切换到 owlclaw database 启用扩展
        await conn.close()
        owlclaw_url = admin_url.replace("/postgres", "/owlclaw")
        conn = await asyncpg.connect(owlclaw_url)
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
    finally:
        await conn.close()
```


### 7. Migrate 命令 (db_migrate.py)

**职责**：
- 执行 Alembic 迁移
- 支持升级到指定版本
- 支持 dry-run 模式

**接口**：

```python
import typer
from typing import Optional
from pathlib import Path
from alembic.config import Config
from alembic import command
from owlclaw.cli.config import get_database_url
from owlclaw.cli.output import print_success, print_error, print_info, progress_spinner
from owlclaw.cli.exceptions import MigrationError

def migrate_command(
    target: Optional[str] = typer.Option(
        None,
        "--target",
        help="目标迁移版本（默认为 head）",
    ),
    database_url: Optional[str] = typer.Option(
        None,
        "--database-url",
        help="数据库连接 URL（覆盖配置）",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="显示将要执行的迁移但不实际执行",
    ),
) -> None:
    """
    执行数据库 schema 迁移。
    
    将数据库升级到最新版本或指定版本。
    """
    try:
        # 获取数据库 URL
        db_url = get_database_url(cli_url=database_url)
        
        # 加载 Alembic 配置
        alembic_cfg = _load_alembic_config(db_url)
        
        # 获取待执行的迁移
        pending_migrations = _get_pending_migrations(alembic_cfg, target or "head")
        
        if not pending_migrations:
            print_info("数据库已是最新版本")
            return
        
        if dry_run:
            print_info("Dry-run 模式，待执行的迁移：")
            for migration in pending_migrations:
                print(f"  - {migration}")
            return
        
        # 执行迁移
        with progress_spinner(f"正在执行 {len(pending_migrations)} 个迁移..."):
            command.upgrade(alembic_cfg, target or "head")
        
        print_success(f"成功应用 {len(pending_migrations)} 个迁移")
        for migration in pending_migrations:
            print_info(f"  ✓ {migration}")
        
    except Exception as e:
        from owlclaw.cli.exceptions import handle_exception
        raise typer.Exit(handle_exception(e))

def _load_alembic_config(database_url: str) -> Config:
    """加载 Alembic 配置"""
    # 查找 alembic.ini
    alembic_ini = Path("alembic.ini")
    if not alembic_ini.exists():
        raise MigrationError(
            "未找到 alembic.ini 文件。\n"
            "请确保在项目根目录执行命令，或运行 'alembic init migrations' 初始化 Alembic。"
        )
    
    # 创建配置对象
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", database_url)
    
    return cfg

def _get_pending_migrations(cfg: Config, target: str) -> list[str]:
    """获取待执行的迁移列表"""
    from alembic.script import ScriptDirectory
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine
    
    # 获取当前版本
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        current_rev = context.get_current_revision()
    
    # 获取脚本目录
    script = ScriptDirectory.from_config(cfg)
    
    # 获取待执行的迁移
    pending = []
    for rev in script.iterate_revisions(target, current_rev):
        pending.append(f"{rev.revision[:8]} - {rev.doc}")
    
    return list(reversed(pending))
```


### 8. Status 命令 (db_status.py)

**职责**：
- 检查数据库连接
- 显示迁移状态
- 显示表统计信息

**接口**：

```python
import typer
from typing import Optional
from owlclaw.cli.config import get_database_url
from owlclaw.cli.output import print_error, print_info, mask_password
from owlclaw.cli.exceptions import DatabaseConnectionError
from sqlalchemy.ext.asyncio import create_async_engine
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext

async def status_command(
    database_url: Optional[str] = typer.Option(
        None,
        "--database-url",
        help="数据库连接 URL（覆盖配置）",
    ),
) -> None:
    """
    检查数据库状态。
    
    显示连接信息、迁移版本、表统计等。
    """
    try:
        # 获取数据库 URL
        db_url = get_database_url(cli_url=database_url)
        
        # 创建引擎
        engine = create_async_engine(db_url)
        
        # 收集状态信息
        status_info = await _collect_status_info(engine, db_url)
        
        # 显示状态
        _print_status(status_info)
        
        await engine.dispose()
        
    except Exception as e:
        from owlclaw.cli.exceptions import handle_exception
        raise typer.Exit(handle_exception(e))

async def _collect_status_info(engine, db_url: str) -> dict:
    """收集数据库状态信息"""
    from sqlalchemy import text
    
    info = {
        "connection": mask_password(db_url),
        "server_version": None,
        "extensions": [],
        "current_migration": None,
        "pending_migrations": 0,
        "table_count": 0,
        "total_rows": 0,
        "disk_usage": 0,
    }
    
    async with engine.connect() as conn:
        # 服务器版本
        result = await conn.execute(text("SELECT version()"))
        version = result.scalar()
        info["server_version"] = version.split(",")[0] if version else "Unknown"
        
        # 扩展
        result = await conn.execute(
            text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'")
        )
        for row in result:
            info["extensions"].append(f"{row[0]} {row[1]}")
        
        # 表统计
        result = await conn.execute(
            text("""
                SELECT COUNT(*) as table_count,
                       SUM(n_live_tup) as total_rows,
                       pg_database_size(current_database()) as disk_usage
                FROM pg_stat_user_tables
            """)
        )
        row = result.fetchone()
        if row:
            info["table_count"] = row[0] or 0
            info["total_rows"] = row[1] or 0
            info["disk_usage"] = row[2] or 0
    
    # 迁移状态
    try:
        alembic_cfg = _load_alembic_config(db_url)
        script = ScriptDirectory.from_config(alembic_cfg)
        
        async with engine.connect() as conn:
            context = MigrationContext.configure(conn.sync_connection)
            current_rev = context.get_current_revision()
            
            if current_rev:
                rev_obj = script.get_revision(current_rev)
                info["current_migration"] = f"{current_rev[:8]} ({rev_obj.doc})"
            else:
                info["current_migration"] = "未初始化"
            
            # 待执行的迁移
            pending = list(script.iterate_revisions("head", current_rev))
            info["pending_migrations"] = len(pending)
    except Exception:
        info["current_migration"] = "无法获取"
        info["pending_migrations"] = 0
    
    return info

def _print_status(info: dict) -> None:
    """打印状态信息"""
    from owlclaw.cli.output import format_size
    
    print("\nOwlClaw Database Status")
    print("=" * 50)
    print(f"Connection:     {info['connection']}")
    print(f"Server:         {info['server_version']}")
    print(f"Extensions:     {', '.join(info['extensions']) or 'None'}")
    print(f"Migration:      {info['current_migration']}")
    print(f"Pending:        {info['pending_migrations']} migrations")
    print(f"Tables:         {info['table_count']}")
    print(f"Total rows:     {info['total_rows']:,}")
    print(f"Disk usage:     {format_size(info['disk_usage'])}")
    print()
```


### 9. Revision 命令 (db_revision.py)

**职责**：
- 生成新的迁移脚本
- 支持 autogenerate 和空模板

**接口**：

```python
import typer
from typing import Optional
from owlclaw.cli.config import get_database_url
from owlclaw.cli.output import print_success, print_warning, print_info
from owlclaw.cli.exceptions import MigrationError
from alembic.config import Config
from alembic import command

def revision_command(
    message: str = typer.Option(
        ...,
        "-m",
        "--message",
        help="迁移描述",
    ),
    empty: bool = typer.Option(
        False,
        "--empty",
        help="生成空的迁移模板",
    ),
    database_url: Optional[str] = typer.Option(
        None,
        "--database-url",
        help="数据库连接 URL（覆盖配置）",
    ),
) -> None:
    """
    生成新的迁移脚本。
    
    默认使用 autogenerate 从模型定义生成迁移。
    """
    try:
        # 获取数据库 URL
        db_url = get_database_url(cli_url=database_url)
        
        # 加载 Alembic 配置
        alembic_cfg = _load_alembic_config(db_url)
        
        # 生成迁移
        if empty:
            print_info("生成空的迁移模板...")
            command.revision(alembic_cfg, message=message)
        else:
            print_info("从模型定义自动生成迁移...")
            command.revision(alembic_cfg, message=message, autogenerate=True)
        
        # 检查生成的迁移
        script_dir = alembic_cfg.get_main_option("script_location")
        latest_revision = _get_latest_revision(alembic_cfg)
        
        if latest_revision:
            revision_file = f"{script_dir}/versions/{latest_revision.revision}_{latest_revision.doc.replace(' ', '_')}.py"
            print_success(f"迁移脚本已生成：{revision_file}")
            print_info(f"Revision ID: {latest_revision.revision}")
            
            # 检查是否包含危险操作
            _check_dangerous_operations(revision_file)
        else:
            print_warning("未检测到模型变化，未生成迁移脚本")
        
    except Exception as e:
        from owlclaw.cli.exceptions import handle_exception
        raise typer.Exit(handle_exception(e))

def _get_latest_revision(cfg: Config):
    """获取最新的迁移版本"""
    from alembic.script import ScriptDirectory
    script = ScriptDirectory.from_config(cfg)
    return script.get_current_head()

def _check_dangerous_operations(revision_file: str) -> None:
    """检查迁移脚本中的危险操作"""
    with open(revision_file) as f:
        content = f.read()
    
    dangerous_ops = []
    if "drop_table" in content:
        dangerous_ops.append("DROP TABLE")
    if "drop_column" in content:
        dangerous_ops.append("DROP COLUMN")
    
    if dangerous_ops:
        from owlclaw.cli.output import print_warning
        print_warning(f"迁移包含危险操作：{', '.join(dangerous_ops)}")
        print_warning("请仔细审查迁移脚本后再执行")
```

### 10. Rollback 命令 (db_rollback.py)

**职责**：
- 回滚数据库迁移
- 支持回滚到指定版本或回滚 N 步

**接口**：

```python
import typer
from typing import Optional
from owlclaw.cli.config import get_database_url
from owlclaw.cli.output import print_success, print_info, print_warning, confirm, progress_spinner
from owlclaw.cli.exceptions import MigrationError
from alembic.config import Config
from alembic import command

def rollback_command(
    target: Optional[str] = typer.Option(
        None,
        "--target",
        help="目标迁移版本",
    ),
    steps: Optional[int] = typer.Option(
        None,
        "--steps",
        help="回滚步数",
    ),
    database_url: Optional[str] = typer.Option(
        None,
        "--database-url",
        help="数据库连接 URL（覆盖配置）",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="显示将要回滚的迁移但不实际执行",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="跳过确认提示",
    ),
) -> None:
    """
    回滚数据库迁移。
    
    默认回滚一个版本，或使用 --target/--steps 指定。
    """
    try:
        # 参数验证
        if target and steps:
            raise MigrationError("--target 和 --steps 不能同时使用")
        
        # 获取数据库 URL
        db_url = get_database_url(cli_url=database_url)
        
        # 加载 Alembic 配置
        alembic_cfg = _load_alembic_config(db_url)
        
        # 计算目标版本
        if steps:
            target_rev = f"-{steps}"
        elif target:
            target_rev = target
        else:
            target_rev = "-1"
        
        # 获取将要回滚的迁移
        rollback_migrations = _get_rollback_migrations(alembic_cfg, target_rev)
        
        if not rollback_migrations:
            print_info("已经是最早版本，无需回滚")
            return
        
        if dry_run:
            print_info("Dry-run 模式，将要回滚的迁移：")
            for migration in rollback_migrations:
                print(f"  - {migration}")
            return
        
        # 确认回滚
        if not yes:
            print_warning(f"将要回滚 {len(rollback_migrations)} 个迁移：")
            for migration in rollback_migrations:
                print(f"  - {migration}")
            if not confirm("确认回滚？", default=False):
                print_info("已取消")
                return
        
        # 执行回滚
        with progress_spinner(f"正在回滚 {len(rollback_migrations)} 个迁移..."):
            command.downgrade(alembic_cfg, target_rev)
        
        print_success(f"成功回滚 {len(rollback_migrations)} 个迁移")
        
    except Exception as e:
        from owlclaw.cli.exceptions import handle_exception
        raise typer.Exit(handle_exception(e))

def _get_rollback_migrations(cfg: Config, target: str) -> list[str]:
    """获取将要回滚的迁移列表"""
    from alembic.script import ScriptDirectory
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine
    
    # 获取当前版本
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        current_rev = context.get_current_revision()
    
    if not current_rev:
        return []
    
    # 获取脚本目录
    script = ScriptDirectory.from_config(cfg)
    
    # 计算目标版本
    if target.startswith("-"):
        steps = int(target[1:])
        revisions = list(script.iterate_revisions(current_rev, "base"))
        if steps > len(revisions):
            target_rev = "base"
        else:
            target_rev = revisions[steps - 1].revision
    else:
        target_rev = target
    
    # 获取将要回滚的迁移
    rollback = []
    for rev in script.iterate_revisions(current_rev, target_rev):
        rollback.append(f"{rev.revision[:8]} - {rev.doc}")
    
    return rollback
```


### 11. Backup 命令 (db_backup.py)

**职责**：
- 使用 pg_dump 备份数据库
- 支持多种备份格式
- 支持 schema-only 和 data-only

**接口**：

```python
import typer
from typing import Optional
from pathlib import Path
import subprocess
from owlclaw.cli.config import get_database_url
from owlclaw.cli.output import (
    print_success, print_error, print_info, print_warning,
    confirm, progress_spinner, format_size
)
from owlclaw.cli.exceptions import BackupError

def backup_command(
    output: Path = typer.Option(
        ...,
        "--output",
        help="备份文件路径",
    ),
    format: str = typer.Option(
        "plain",
        "--format",
        help="备份格式：plain（SQL）或 custom（pg_restore 格式）",
    ),
    schema_only: bool = typer.Option(
        False,
        "--schema-only",
        help="只备份 schema，不备份数据",
    ),
    data_only: bool = typer.Option(
        False,
        "--data-only",
        help="只备份数据，不备份 schema",
    ),
    database_url: Optional[str] = typer.Option(
        None,
        "--database-url",
        help="数据库连接 URL（覆盖配置）",
    ),
) -> None:
    """
    备份 owlclaw database。
    
    使用 pg_dump 创建数据库备份。
    """
    try:
        # 参数验证
        if schema_only and data_only:
            raise BackupError("--schema-only 和 --data-only 不能同时使用")
        
        if format not in ("plain", "custom"):
            raise BackupError(f"不支持的格式：{format}。支持的格式：plain, custom")
        
        # 检查 pg_dump
        if not _check_pg_dump():
            raise BackupError(
                "未找到 pg_dump 工具。\n"
                "请安装 PostgreSQL 客户端工具：\n"
                "  - Ubuntu/Debian: apt install postgresql-client\n"
                "  - macOS: brew install postgresql\n"
                "  - Windows: 从 PostgreSQL 官网下载安装"
            )
        
        # 检查输出文件
        if output.exists():
            if not confirm(f"文件 {output} 已存在，是否覆盖？", default=False):
                print_info("已取消")
                return
        
        # 获取数据库 URL
        db_url = get_database_url(cli_url=database_url)
        
        # 构建 pg_dump 命令
        cmd = _build_pg_dump_command(
            db_url=db_url,
            output=output,
            format=format,
            schema_only=schema_only,
            data_only=data_only,
        )
        
        # 执行备份
        with progress_spinner("正在备份数据库..."):
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                # 删除不完整的备份文件
                if output.exists():
                    output.unlink()
                raise BackupError(f"备份失败：{result.stderr}")
        
        # 显示结果
        file_size = output.stat().st_size
        print_success(f"备份完成：{output}")
        print_info(f"文件大小：{format_size(file_size)}")
        
    except Exception as e:
        from owlclaw.cli.exceptions import handle_exception
        raise typer.Exit(handle_exception(e))

def _check_pg_dump() -> bool:
    """检查 pg_dump 是否可用"""
    try:
        subprocess.run(["pg_dump", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def _build_pg_dump_command(
    db_url: str,
    output: Path,
    format: str,
    schema_only: bool,
    data_only: bool,
) -> list[str]:
    """构建 pg_dump 命令"""
    from urllib.parse import urlparse
    
    # 解析 URL
    parsed = urlparse(db_url)
    
    cmd = [
        "pg_dump",
        "-h", parsed.hostname or "localhost",
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "postgres",
        "-d", parsed.path.lstrip("/"),
        "-f", str(output),
    ]
    
    # 格式
    if format == "custom":
        cmd.extend(["-F", "c"])
    
    # Schema/Data only
    if schema_only:
        cmd.append("--schema-only")
    elif data_only:
        cmd.append("--data-only")
    
    # 设置密码环境变量
    if parsed.password:
        import os
        os.environ["PGPASSWORD"] = parsed.password
    
    return cmd
```


### 12. Restore 命令 (db_restore.py)

**职责**：
- 从备份恢复数据库
- 支持 SQL 和 custom 格式
- 提供安全确认

**接口**：

```python
import typer
from typing import Optional
from pathlib import Path
import subprocess
from owlclaw.cli.config import get_database_url
from owlclaw.cli.output import (
    print_success, print_error, print_info, print_warning,
    confirm, progress_spinner
)
from owlclaw.cli.exceptions import RestoreError

def restore_command(
    input: Path = typer.Option(
        ...,
        "--input",
        help="备份文件路径",
    ),
    clean: bool = typer.Option(
        False,
        "--clean",
        help="恢复前清空目标数据库",
    ),
    database_url: Optional[str] = typer.Option(
        None,
        "--database-url",
        help="数据库连接 URL（覆盖配置）",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="跳过确认提示",
    ),
) -> None:
    """
    从备份恢复数据库。
    
    支持 SQL 和 custom 格式的备份文件。
    """
    try:
        # 检查备份文件
        if not input.exists():
            raise RestoreError(f"备份文件不存在：{input}")
        
        # 获取数据库 URL
        db_url = get_database_url(cli_url=database_url)
        
        # 检查数据库是否为空
        if not clean and not yes:
            is_empty = await _check_database_empty(db_url)
            if not is_empty:
                print_warning("目标数据库不为空")
                if not confirm("继续恢复可能覆盖现有数据，是否继续？", default=False):
                    print_info("已取消")
                    return
        
        # 确认恢复
        if not yes:
            print_warning(f"将从 {input} 恢复数据库")
            if clean:
                print_warning("将先清空目标数据库")
            if not confirm("确认恢复？", default=False):
                print_info("已取消")
                return
        
        # 检测备份格式
        backup_format = _detect_backup_format(input)
        
        # 执行恢复
        with progress_spinner("正在恢复数据库..."):
            if backup_format == "sql":
                _restore_from_sql(db_url, input, clean)
            else:
                _restore_from_custom(db_url, input, clean)
        
        # 显示结果
        stats = await _get_restore_stats(db_url)
        print_success("恢复完成")
        print_info(f"表数量：{stats['table_count']}")
        print_info(f"总行数：{stats['total_rows']:,}")
        
    except Exception as e:
        from owlclaw.cli.exceptions import handle_exception
        raise typer.Exit(handle_exception(e))

async def _check_database_empty(db_url: str) -> bool:
    """检查数据库是否为空"""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    
    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM pg_stat_user_tables")
            )
            count = result.scalar()
            return count == 0
    finally:
        await engine.dispose()

def _detect_backup_format(input: Path) -> str:
    """检测备份文件格式"""
    # 读取文件头
    with open(input, "rb") as f:
        header = f.read(5)
    
    # pg_dump custom 格式的魔数
    if header == b"PGDMP":
        return "custom"
    else:
        return "sql"

def _restore_from_sql(db_url: str, input: Path, clean: bool) -> None:
    """从 SQL 文件恢复"""
    from urllib.parse import urlparse
    
    parsed = urlparse(db_url)
    
    cmd = [
        "psql",
        "-h", parsed.hostname or "localhost",
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "postgres",
        "-d", parsed.path.lstrip("/"),
        "-f", str(input),
    ]
    
    if clean:
        cmd.append("--clean")
    
    # 设置密码环境变量
    if parsed.password:
        import os
        os.environ["PGPASSWORD"] = parsed.password
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RestoreError(f"恢复失败：{result.stderr}")

def _restore_from_custom(db_url: str, input: Path, clean: bool) -> None:
    """从 custom 格式恢复"""
    from urllib.parse import urlparse
    
    parsed = urlparse(db_url)
    
    cmd = [
        "pg_restore",
        "-h", parsed.hostname or "localhost",
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "postgres",
        "-d", parsed.path.lstrip("/"),
        str(input),
    ]
    
    if clean:
        cmd.append("--clean")
    
    # 设置密码环境变量
    if parsed.password:
        import os
        os.environ["PGPASSWORD"] = parsed.password
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RestoreError(f"恢复失败：{result.stderr}")

async def _get_restore_stats(db_url: str) -> dict:
    """获取恢复后的统计信息"""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    
    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT COUNT(*) as table_count,
                           SUM(n_live_tup) as total_rows
                    FROM pg_stat_user_tables
                """)
            )
            row = result.fetchone()
            return {
                "table_count": row[0] or 0,
                "total_rows": row[1] or 0,
            }
    finally:
        await engine.dispose()
```


### 13. Check 命令 (db_check.py)

**职责**：
- 执行数据库健康检查
- 检查连接、迁移、扩展、连接池、磁盘、慢查询

**接口**：

```python
import typer
from typing import Optional
from owlclaw.cli.config import get_database_url
from owlclaw.cli.output import print_info
from owlclaw.cli.exceptions import DatabaseConnectionError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import time

async def check_command(
    database_url: Optional[str] = typer.Option(
        None,
        "--database-url",
        help="数据库连接 URL（覆盖配置）",
    ),
) -> None:
    """
    数据库健康检查。
    
    检查连接、迁移、扩展、连接池、磁盘使用等。
    """
    try:
        # 获取数据库 URL
        db_url = get_database_url(cli_url=database_url)
        
        # 创建引擎
        engine = create_async_engine(db_url)
        
        # 执行检查
        checks = await _run_health_checks(engine, db_url)
        
        # 显示结果
        _print_health_report(checks)
        
        await engine.dispose()
        
        # 根据检查结果设置退出码
        if any(c["status"] == "ERROR" for c in checks):
            raise typer.Exit(1)
        
    except Exception as e:
        from owlclaw.cli.exceptions import handle_exception
        raise typer.Exit(handle_exception(e))

async def _run_health_checks(engine, db_url: str) -> list[dict]:
    """运行所有健康检查"""
    checks = []
    
    # 1. 连接检查
    checks.append(await _check_connection(engine))
    
    # 2. 迁移检查
    checks.append(await _check_migration(db_url))
    
    # 3. pgvector 扩展检查
    checks.append(await _check_pgvector(engine))
    
    # 4. 连接池检查
    checks.append(await _check_connection_pool(engine))
    
    # 5. 磁盘使用检查
    checks.append(await _check_disk_usage(engine))
    
    # 6. 慢查询检查
    checks.append(await _check_slow_queries(engine))
    
    return checks

async def _check_connection(engine) -> dict:
    """检查数据库连接"""
    try:
        start = time.time()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000
        
        if latency < 10:
            status = "OK"
        elif latency < 100:
            status = "WARN"
        else:
            status = "ERROR"
        
        return {
            "name": "Connection",
            "status": status,
            "message": f"responsive ({latency:.0f}ms)",
        }
    except Exception as e:
        return {
            "name": "Connection",
            "status": "ERROR",
            "message": f"failed - {e}",
        }

async def _check_migration(db_url: str) -> dict:
    """检查迁移状态"""
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from alembic.runtime.migration import MigrationContext
        from sqlalchemy import create_engine
        
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        
        script = ScriptDirectory.from_config(alembic_cfg)
        engine = create_engine(db_url.replace("+asyncpg", ""))
        
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
            
            if not current_rev:
                return {
                    "name": "Migration",
                    "status": "WARN",
                    "message": "not initialized",
                }
            
            pending = list(script.iterate_revisions("head", current_rev))
            
            if pending:
                return {
                    "name": "Migration",
                    "status": "WARN",
                    "message": f"{len(pending)} pending migrations",
                }
            else:
                return {
                    "name": "Migration",
                    "status": "OK",
                    "message": f"up to date ({current_rev[:8]})",
                }
    except Exception as e:
        return {
            "name": "Migration",
            "status": "ERROR",
            "message": f"check failed - {e}",
        }

async def _check_pgvector(engine) -> dict:
    """检查 pgvector 扩展"""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            )
            version = result.scalar()
            
            if version:
                return {
                    "name": "pgvector",
                    "status": "OK",
                    "message": f"installed ({version})",
                }
            else:
                return {
                    "name": "pgvector",
                    "status": "WARN",
                    "message": "not installed",
                }
    except Exception as e:
        return {
            "name": "pgvector",
            "status": "ERROR",
            "message": f"check failed - {e}",
        }

async def _check_connection_pool(engine) -> dict:
    """检查连接池使用率"""
    try:
        pool = engine.pool
        size = pool.size()
        checked_out = pool.checkedout()
        
        usage_percent = (checked_out / size * 100) if size > 0 else 0
        
        if usage_percent < 70:
            status = "OK"
        elif usage_percent < 90:
            status = "WARN"
        else:
            status = "ERROR"
        
        return {
            "name": "Connection pool",
            "status": status,
            "message": f"{checked_out}/{size} active ({usage_percent:.0f}%)",
        }
    except Exception as e:
        return {
            "name": "Connection pool",
            "status": "ERROR",
            "message": f"check failed - {e}",
        }

async def _check_disk_usage(engine) -> dict:
    """检查磁盘使用"""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT pg_database_size(current_database())")
            )
            size_bytes = result.scalar()
            
            from owlclaw.cli.output import format_size
            size_str = format_size(size_bytes)
            
            # 简单检查：超过 10GB 警告
            if size_bytes < 10 * 1024 * 1024 * 1024:
                status = "OK"
            else:
                status = "WARN"
            
            return {
                "name": "Disk usage",
                "status": status,
                "message": size_str,
            }
    except Exception as e:
        return {
            "name": "Disk usage",
            "status": "ERROR",
            "message": f"check failed - {e}",
        }

async def _check_slow_queries(engine) -> dict:
    """检查慢查询"""
    try:
        async with engine.connect() as conn:
            # 检查最近一小时内执行时间超过 1 秒的查询
            result = await conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM pg_stat_statements
                    WHERE mean_exec_time > 1000
                      AND calls > 0
                """)
            )
            slow_count = result.scalar() or 0
            
            if slow_count == 0:
                status = "OK"
                message = "no slow queries"
            elif slow_count < 5:
                status = "WARN"
                message = f"{slow_count} queries > 1s"
            else:
                status = "ERROR"
                message = f"{slow_count} queries > 1s"
            
            return {
                "name": "Slow queries",
                "status": status,
                "message": message,
            }
    except Exception:
        # pg_stat_statements 可能未启用
        return {
            "name": "Slow queries",
            "status": "OK",
            "message": "N/A (pg_stat_statements not enabled)",
        }

def _print_health_report(checks: list[dict]) -> None:
    """打印健康检查报告"""
    print("\nOwlClaw Database Health Check")
    print("=" * 50)
    
    for check in checks:
        status = check["status"]
        name = check["name"]
        message = check["message"]
        
        if status == "OK":
            icon = "[OK] "
            color = ""
        elif status == "WARN":
            icon = "[WARN]"
            color = ""
        else:
            icon = "[ERROR]"
            color = ""
        
        print(f"{icon:6} {name:20} {message}")
    
    # 总体状态
    error_count = sum(1 for c in checks if c["status"] == "ERROR")
    warn_count = sum(1 for c in checks if c["status"] == "WARN")
    
    print()
    if error_count > 0:
        print(f"Overall: UNHEALTHY ({error_count} errors, {warn_count} warnings)")
    elif warn_count > 0:
        print(f"Overall: HEALTHY ({warn_count} warnings)")
    else:
        print("Overall: HEALTHY")
    print()
```

## 数据模型

CLI 工具不直接定义数据模型，但会与以下数据库对象交互：

### Alembic 迁移表

```sql
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);
```

### PostgreSQL 系统表

CLI 工具会查询以下系统表获取状态信息：

- `pg_stat_user_tables`：表统计信息
- `pg_extension`：已安装的扩展
- `pg_database_size()`：数据库大小
- `pg_stat_statements`：查询统计（如果启用）


## 正确性属性

属性是一种特征或行为，应该在系统的所有有效执行中保持为真——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。

### 属性 1：配置优先级一致性

*对于任何* CLI 命令，当从多个配置源读取 Database_URL 时，应该遵循优先级：命令行参数 > 环境变量 > 配置文件。

**验证需求：9.1, 9.2, 9.3**

### 属性 2：退出码正确性

*对于任何* CLI 命令，当命令执行成功时应该以退出码 0 退出，当命令执行失败时应该以非零退出码退出。

**验证需求：10.2, 10.3**

### 属性 3：参数验证一致性

*对于任何* 无效的命令行参数（URL 格式、文件路径、数字参数等），CLI 应该显示清晰的错误消息，包含错误原因和正确格式示例。

**验证需求：12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7**

## 错误处理

### 错误类型层次

```
CLIError (基础异常)
├── ConfigurationError (配置错误)
├── DatabaseConnectionError (数据库连接错误)
├── MigrationError (迁移错误)
├── BackupError (备份错误)
└── RestoreError (恢复错误)
```

### 错误场景和处理策略

| 场景 | 异常类型 | 错误消息内容 | 恢复策略 |
|------|---------|-------------|---------|
| 未配置 Database_URL | ConfigurationError | "未找到数据库连接配置。请设置 OWLCLAW_DATABASE_URL..." | 用户配置环境变量或配置文件 |
| URL 格式无效 | ValueError | "无效的数据库 URL 格式：{url}\\n期望格式：postgresql://..." | 用户修正 URL 格式 |
| 数据库连接失败 | DatabaseConnectionError | "无法连接到 {host}:{port} - {message}" | 检查网络和数据库状态 |
| Alembic 配置缺失 | MigrationError | "未找到 alembic.ini 文件。请确保在项目根目录..." | 用户初始化 Alembic |
| 迁移执行失败 | MigrationError | "迁移失败：{revision} - {error}" | 检查迁移脚本和数据库状态 |
| pg_dump 不可用 | BackupError | "未找到 pg_dump 工具。请安装 PostgreSQL 客户端..." | 用户安装 PostgreSQL 客户端 |
| 备份文件不存在 | RestoreError | "备份文件不存在：{path}" | 用户提供正确的文件路径 |
| 用户中断操作 | KeyboardInterrupt | "操作已取消" | 清理临时资源并退出 |

### 错误处理原则

1. **清晰的错误消息**：包含错误原因和解决建议
2. **不暴露敏感信息**：错误消息中隐藏密码
3. **提供上下文**：包含足够的信息帮助诊断（主机、端口、文件路径等）
4. **可操作性**：错误消息应该指导用户如何修复问题
5. **优雅退出**：捕获 KeyboardInterrupt，清理临时资源

## 测试策略

### 双重测试方法

CLI 数据库运维工具需要同时使用单元测试和基于属性的测试：

- **单元测试**：验证特定命令的具体场景、边缘情况和错误条件
- **基于属性的测试**：验证跨所有命令的通用属性

两者是互补的，共同提供全面的覆盖。

### 单元测试重点

单元测试应该专注于：

1. **特定命令场景**：
   - `init` 命令创建 database 和 role
   - `migrate` 命令执行迁移
   - `status` 命令显示正确的状态信息
   - `backup` 命令生成备份文件
   - `restore` 命令恢复数据
   - `check` 命令执行健康检查

2. **边缘情况**：
   - database 已存在时的处理
   - 没有待执行迁移时的输出
   - 备份文件已存在时的确认
   - 空数据库的恢复

3. **错误条件**：
   - 数据库连接失败
   - Alembic 配置缺失
   - pg_dump 不可用
   - 无效的参数组合

4. **用户交互**：
   - dry-run 模式不修改数据库
   - 确认提示的处理
   - --yes 参数跳过确认

### 基于属性的测试

基于属性的测试应该验证：

1. **属性 1-3**：如正确性属性部分所述
2. **测试配置**：每个属性测试至少运行 100 次迭代
3. **标签格式**：`Feature: cli-db, Property N: [属性描述]`

### 测试库选择

- **Python**：使用 `hypothesis` 进行基于属性的测试
- **单元测试框架**：使用 `pytest`
- **CLI 测试**：使用 `typer.testing.CliRunner`
- **数据库测试**：使用 Docker 容器提供测试数据库

### 测试隔离

- 每个测试使用独立的测试数据库
- 测试前创建测试数据库，测试后清理
- 使用 pytest fixtures 管理测试数据库生命周期
- 模拟 pg_dump/pg_restore 调用以避免依赖外部工具

### 集成测试

虽然本模块主要是 CLI 工具，但仍需要一些集成测试：

- 实际连接到 PostgreSQL 数据库
- 测试 Alembic 迁移的完整流程
- 测试备份和恢复的端到端流程
- 测试健康检查的实际查询

这些集成测试应该标记为 `@pytest.mark.integration`，可以在 CI 中选择性运行。

## 实现注意事项

### 性能考虑

1. **异步操作**：数据库操作使用异步 API，避免阻塞
2. **进度显示**：长时间操作显示进度指示器
3. **连接复用**：在同一命令中复用数据库连接

### 安全考虑

1. **密码保护**：输出中隐藏密码
2. **环境变量**：使用 PGPASSWORD 传递密码给 pg_dump/pg_restore
3. **确认提示**：危险操作（如恢复、回滚）需要用户确认

### 可维护性

1. **类型注解**：所有函数使用类型注解
2. **文档字符串**：所有命令函数包含详细的文档字符串
3. **错误消息**：清晰、可操作的错误消息
4. **模块化**：每个命令独立模块，便于维护

### 用户体验

1. **一致的输出格式**：使用 rich 库提供美观的输出
2. **颜色编码**：成功（绿色）、警告（黄色）、错误（红色）
3. **进度反馈**：长时间操作显示旋转器
4. **帮助信息**：每个命令提供详细的帮助文本

### 向后兼容性

1. **API 稳定性**：命令参数保持稳定，避免破坏性变更
2. **弃用策略**：使用警告标记弃用的参数
3. **版本管理**：遵循语义化版本控制

### 未来扩展

1. **多数据库支持**：支持连接多个数据库
2. **并行迁移**：支持并行执行多个迁移
3. **迁移验证**：在执行前验证迁移脚本的安全性
4. **自动备份**：在执行危险操作前自动备份
5. **Cloud 支持**：支持 Cloud 环境的特殊需求（RLS 等）

