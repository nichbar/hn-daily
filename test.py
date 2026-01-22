import asyncio
import logging
import os
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 获取项目根目录（找到 .claude 所在目录）
PROJECT_ROOT = Path(__file__).parent
logger.info(f"项目根目录: {PROJECT_ROOT}")

async def main():
    logger.info("开始执行查询...")

    try:
        async for message in query(
            prompt="\\/daily",
            options=ClaudeAgentOptions(
                permission_mode="acceptEdits",
                allowed_tools=["Bash", "Read", "Glob"],
            )
        ):
            # 记录消息类型
            msg_type = type(message).__name__
            logger.debug(f"收到消息类型: {msg_type}")

            # 处理内容块
            if hasattr(message, "content") and message.content:
                for block in message.content:
                    if hasattr(block, "text"):
                        text = block.text
                        if text:
                            logger.info(f"[Claude]: {text}")
                    elif hasattr(block, "type"):
                        logger.debug(f"内容块类型: {block.type}")

            # 记录结果消息
            if hasattr(message, 'result'):
                logger.info(f"[结果]: {message.result}")

            # 记录是否错误
            if hasattr(message, 'error') and message.error:
                logger.error(f"[错误]: {message.error}")

    except Exception as e:
        logger.error(f"执行出错: {e}")
        raise

    logger.info("查询完成!")

if __name__ == "__main__":
    logger.info("启动 Claude SDK 测试...")
    asyncio.run(main())
