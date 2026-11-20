# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic browser editor state checks, with no host clipboard access."""
from playwright.sync_api import expect


def focus_editor(page, index):
    field = page.get_by_role('textbox').nth(index)
    field.click()
    expect(field).to_be_focused()
    # Flutter's DOM focus event requests a semantics focus action. The engine
    # activates the editor later, when its input configuration applies these
    # autofill IDs. DOM focus alone does not establish an active input channel.
    expect(field).to_have_attribute('id', 'username' if index == 0 else 'current-password')
    return field


def field_metadata(field, expected):
    return field.evaluate("""(element, expected) => ({
        type: typeof element.value,
        length: typeof element.value === 'string' ? element.value.length : null,
        exact: element.value === expected,
        masked: element.type === 'password',
        selectionStart: element.selectionStart,
        selectionEnd: element.selectionEnd,
        engineConfigured: element.id === (element.type === 'password' ? 'current-password' : 'username')
    })""", expected)


def replace_with_keys(page, text):
    page.keyboard.press('ControlOrMeta+A')
    page.keyboard.press('Backspace')
    page.keyboard.type(text, delay=25)
