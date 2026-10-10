# robo page

`RoboPage` provides reusable page-level browser operations. Use
`wait_for_text_visible()` when the next step depends on text becoming visible.
Timeout values are in **seconds**; when `timeout` is omitted, the configured
browser/default wait timeout applies.

```python
page.wait_for_text_visible("Ready")
page.wait_for_text_visible("Processing complete", timeout=8)
page.wait_for_text_visible("partial message", exact=False)
```

::: robo_automation.framework.robo_page.RoboPage
    options:
      members:
        - goto
        - reload
        - title
        - close
        - is_closed
        - bring_to_front
        - content
        - screenshot
        - evaluate
        - wait_for_load_state
        - wait_for_text_visible
        - press
        - press_key
        - same_page
        - same_context
        - open_pages
        - get_by_attributes
        - get_by_id
