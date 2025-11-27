import asyncio
import logging
from pathlib import Path
from src.core.robot_controller import RobotController
from src.config.settings import Settings
from src.utils.logger import setup_logger

def main():
    """Main application entry point"""
    # Setup logging
    setup_logger()
    logger = logging.getLogger(__name__)
    
    # Load configuration
    settings = Settings()
    
    # Initialize robot controller
    robot = RobotController(settings)
    
    logger.info("🤖 STEP 1: Robot Greeting Test Starting...")
    logger.info(f"Mode: {settings.ENVIRONMENT}")
    logger.info(f"Voice Provider: {settings.SPEECH_PROVIDER}")
    
    try:
        # Start the robot (Step 1: Just greeting)
        asyncio.run(robot.start())
    except KeyboardInterrupt:
        logger.info("Robot stopped by user")
    except Exception as e:
        logger.error(f"Robot error: {e}")
    finally:
        robot.cleanup()

if __name__ == "__main__":
    main()
