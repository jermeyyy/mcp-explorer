"""Test splash screen display."""
import asyncio
from mcp_explorer.ui.screens import SplashScreen
from textual.app import App


class TestApp(App):
    """Test app to verify splash screen works."""

    def on_mount(self) -> None:
        """Show splash screen on mount."""
        self.run_worker(self._animate_splash, exclusive=True)

    async def _animate_splash(self) -> None:
        """Animate the splash screen."""
        # Create and push splash screen
        splash = SplashScreen()
        await self.push_screen(splash)

        # Wait for it to render
        await asyncio.sleep(0.5)

        print(f"Current screen: {type(self.screen).__name__}")
        print("Splash screen is active!")

        for i in range(4):
            await asyncio.sleep(1.0)
            splash.update_status(f"Step {i+1}/4", (i+1) * 25)
            print(f"Updated splash: Step {i+1}")

        await asyncio.sleep(1.0)
        print("Exiting...")
        self.exit()


if __name__ == "__main__":
    app = TestApp()
    app.run()

