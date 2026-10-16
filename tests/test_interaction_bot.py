from unittest.mock import MagicMock, patch
from src.interaction_bot import FacebookInteractionBot


def test_interaction_bot_init():
    mock_page = MagicMock()
    bot = FacebookInteractionBot(page=mock_page)
    assert bot.page == mock_page
    assert not bot._stopped
    bot.stop()
    assert bot._stopped


@patch("time.sleep", return_value=None)
def test_interaction_bot_stop_during_run(mock_sleep):
    mock_page = MagicMock()
    # Mock locator returning 0 articles to exit loop quickly
    mock_locator = MagicMock()
    mock_locator.count.return_value = 0
    mock_page.locator.return_value = mock_locator

    bot = FacebookInteractionBot(page=mock_page)

    def stop_callback(msg):
        bot.stop()

    stats = bot.interact_with_feed(
        target_url="https://www.facebook.com/",
        total_scrolls=5,
        safe_delay_min=0.01,
        safe_delay_max=0.02,
        log_callback=stop_callback,
    )
    assert bot._stopped
    assert stats["posts_read"] == 0


@patch("time.sleep", return_value=None)
def test_interaction_bot_human_scroll(mock_sleep):
    mock_page = MagicMock()
    bot = FacebookInteractionBot(page=mock_page)
    bot.human_scroll(scroll_steps=2)
    assert mock_page.mouse.wheel.called
