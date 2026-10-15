# robo page

`RoboPage` provides reusable page-level browser operations. For Appian pages,
wait for displayed text through the text component:

```python
page.text("Ready").wait_until_visible()
page.text("Processing complete", timeout=8).wait_until_visible()
page.text("partial message", exact=False).wait_until_visible()
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
        - press
        - press_key
        - same_page
        - same_context
        - open_pages
        - get_by_attributes
        - get_by_id
