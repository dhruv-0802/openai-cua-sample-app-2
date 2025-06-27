import os
from typing import Tuple
from playwright.sync_api import Browser, Page, Error as PlaywrightError
from hyperbrowser import Hyperbrowser
from hyperbrowser.models import CreateSessionParams, ScreenConfig
from dotenv import load_dotenv

from ..shared.base_playwright import BasePlaywrightComputer


load_dotenv()


class HyperbrowserBrowser(BasePlaywrightComputer):
    """
    Hyperbrowser is the next-generation platform for effortless, scalable browser automation. It provides a cloud-based browser instance
    that can be controlled through code, eliminating the need for local infrastructure setup.
    Key features include:
    - Instant Scalability: Spin up hundreds of browser sessions in seconds without infrastructure headaches
    - Simple Integration: Works seamlessly with popular tools like Puppeteer and Playwright
    - Powerful APIs: Easy to use APIs for managing sessions, scraping/crawling any site, and much more
    - Production Ready: Enterprise-grade reliability and security built-in
    - Bypass Anti-Bot Measures: Built-in stealth mode, ad blocking, automatic CAPTCHA solving, and rotating proxies
    IMPORTANT: This Hyperbrowser computer requires the use of the `goto` tool defined in playwright_with_custom_functions.py.
    Make sure to include this tool in your configuration when using the Hyperbrowser computer.
    """

    def get_dimensions(self):
        return self.dimensions

    def __init__(
        self,
        width: int = 1024,
        height: int = 768,
        use_proxy: bool = False,
        adblock: bool = False,
        block_trackers: bool = False,
        block_annoyances: bool = False,
        accept_cookies: bool = False,
    ):
        """
        Initialize the Hyperbrowser session.
        Additional configuration options for a Hyperbrowser session can be found in the Hyperbrowser documentation: https://docs.hyperbrowser.ai/sessions/overview/session-parameters
        Args:
            width (int): The width of the browser viewport. Default is 1024.
            height (int): The height of the browser viewport. Default is 768.
            use_proxy (bool): Whether to use a proxy for the session. Default is False.
            adblock (bool): Whether to block ads and other unwanted content. Default is False.
            block_trackers (bool): Whether to block web trackers and other privacy-invasive technologies. Default is False.
            block_annoyances (bool): Whether to block common annoyances like pop-ups, overlays, and other disruptive elements. Default is False.
            accept_cookies (bool): Whether to accept all cookies on sites that are visited. Default is False.
        """
        super().__init__()
        self.hb = Hyperbrowser(api_key=os.getenv("HYPERBROWSER_API_KEY"))
        self.session = None
        self.dimensions = (width, height)
        self.use_proxy = use_proxy
        self.adblock = adblock
        self.block_trackers = block_trackers
        self.block_annoyances = block_annoyances
        self.accept_cookies = accept_cookies

    def _get_browser_and_page(self) -> Tuple[Browser, Page]:
        """
        Create a Hyperbrowser session and connect to it.
        This method creates a cloud-based browser session using Hyperbrowser's Sessions API,
        configures it with the specified parameters, and establishes a connection using Playwright.
        Returns:
            Tuple[Browser, Page]: A tuple containing the connected browser and page objects.
        """
        # Create a session on Hyperbrowser with specified parameters
        # To view all session parameters, see the Hyperbrowser Sessions API Reference: https://docs.hyperbrowser.ai/reference/api-reference/sessions#post-api-session
        width, height = self.dimensions
        session_params = CreateSessionParams(
            use_proxy=self.use_proxy,
            adblock=self.adblock,
            trackers=self.block_trackers,
            annoyances=self.block_annoyances,
            accept_cookies=self.accept_cookies,
            screen=ScreenConfig(width=width, height=height),
        )
        self.session = self.hb.sessions.create(session_params)

        # Print the live session URL
        print(f"Watch and control this browser live at {self.session.live_url}")

        # Connect to the remote session
        browser = self._playwright.chromium.connect_over_cdp(
            self.session.ws_endpoint, timeout=60000
        )
        context = browser.contexts[0]

        # Add event listeners for page creation and closure
        context.on("page", self._handle_new_page)

        page = context.pages[0]
        page.set_viewport_size({"width": width, "height": height})
        page.on("close", self._handle_page_close)

        page.goto("https://bing.com")

        return browser, page

    def _handle_new_page(self, page: Page):
        """Handle the creation of a new page."""
        print("New page created via event")
        # Only handle the page if it's not already being handled by new_tab or new_tab_go_to
        if self._page != page:
            try:
                if not page.is_closed():
                    self._page = page
                    self._page.set_viewport_size(
                        {"width": self.dimensions[0], "height": self.dimensions[1]}
                    )
                    page.on("close", self._handle_page_close)
            except Exception as e:
                print(f"Warning: Could not set viewport size for new page: {e}")
                self._page = page
                page.on("close", self._handle_page_close)

    def _handle_page_close(self, page: Page):
        """Handle the closure of a page."""
        print("Page closed")
        if self._page == page:
            if self._browser.contexts[0].pages:
                self._page = self._browser.contexts[0].pages[-1]
            else:
                print("Warning: All pages have been closed.")
                self._page = None

    def new_tab(self):
        """Create a new tab and switch to it."""
        try:
            print("Creating new tab directly")
            new_page = self._page.context.new_page()
            # Set viewport size before setting as current page
            new_page.set_viewport_size({"width": self.dimensions[0], "height": self.dimensions[1]})
            new_page.on("close", self._handle_page_close)
            self._page = new_page
            print(f"New tab created successfully, current URL: {self._page.url}")
        except Exception as e:
            print(f"Error creating new tab: {e}")
            raise

    # def get_weather(self, location: str, unit: str) -> str:
    #     """
    #     Call API to get weather
    #     """
    #     try:
    #         # Using OpenWeatherMap API (free tier)
    #         # You'll need to get a free API key from https://openweathermap.org/api
    #         api_key = os.getenv("OPENWEATHER_API_KEY")
    #         if not api_key:
    #             return "Error: OPENWEATHER_API_KEY environment variable not set. Please get a free API key from https://openweathermap.org/api"
            
    #         # Convert unit to OpenWeatherMap format
    #         units = "metric" if unit == "c" else "imperial"
            
    #         # Make API request
    #         url = f"http://api.openweathermap.org/data/2.5/weather"
    #         params = {
    #             "q": location,
    #             "appid": api_key,
    #             "units": units
    #         }
            
    #         response = requests.get(url, params=params, timeout=10)
    #         response.raise_for_status()
            
    #         data = response.json()
            
    #         # Extract only temperature
    #         temp = data["main"]["temp"]
    #         temp_unit = "°C" if unit == "c" else "°F"
            
    #         return f"{temp}{temp_unit}"
            
    #     except requests.exceptions.RequestException as e:
    #         return f"Error: {str(e)}"
    #     except KeyError as e:
    #         return f"Error: {str(e)}"
    #     except Exception as e:
    #         return f"Error: {str(e)}"
        
    # def new_tab_go_to(self, url: str, timeout: float = None, wait_until: str = "load"):
    #     """Create a new tab and navigate to the specified URL."""
    #     try:
    #         print("Creating new tab with URL directly")
    #         new_page = self._page.context.new_page()
    #         # Set viewport size before setting as current page
    #         new_page.set_viewport_size({"width": self.dimensions[0], "height": self.dimensions[1]})
    #         new_page.on("close", self._handle_page_close)
    #         self._page = new_page
            
    #         try:
    #             result = self._page.goto(url)
    #             print(f"New tab created and navigated to: {url}")
    #             return result
    #         except Exception as e:
    #             print(f"Error navigating to {url}: {e}")
    #             return None
    #     except Exception as e:
    #         print(f"Error creating new tab and navigating to {url}: {e}")
    #         raise

    # def switch_tab(self, tab_index: int):
    #     """Switch to a specific tab by index (1-based)."""
    #     pages = self._browser.contexts[0].pages
    #     if 1 <= tab_index <= len(pages):
    #         self._page = pages[tab_index - 1]  # Convert to 0-based index
    #         # Bring the tab to the front
    #         self._page.bring_to_front()
    #         print(f"Switched to tab {tab_index}")
    #     else:
    #         print(f"Tab index {tab_index} out of range. Available tabs: 1-{len(pages)}")
    #         raise ValueError(f"Tab index {tab_index} out of range")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Clean up resources when exiting the context manager.
        Args:
            exc_type: The type of the exception that caused the context to be exited.
            exc_val: The exception instance that caused the context to be exited.
            exc_tb: A traceback object encapsulating the call stack at the point where the exception occurred.
        """
        if self._playwright:
            self._playwright.stop()
        if self._page or self._browser:
            if self.session:
                self.hb.sessions.stop(self.session.id)
            else:
                if self._page:
                    self._page.close()
                if self._browser:
                    self._browser.close()

        if self.session:
            print(
                f"Session completed. View replay at https://app.hyperbrowser.ai/features/sessions/{self.session.id}"
            )

    def screenshot(self) -> str:
        """
        Capture a screenshot of the current viewport using CDP.
        Returns:
            str: A base64 encoded string of the screenshot.
        """
        try:
            # Get CDP session from the page
            cdp_session = self._page.context.new_cdp_session(self._page)

            # Capture screenshot using CDP
            result = cdp_session.send(
                "Page.captureScreenshot", {"format": "png", "fromSurface": True}
            )

            return result["data"]
        except PlaywrightError as error:
            print(
                f"CDP screenshot failed, falling back to standard screenshot: {error}"
            )
            return super().screenshot()