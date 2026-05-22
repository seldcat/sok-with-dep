package com.crawljax.examples.stateabstractions.dep;

import com.crawljax.browser.EmbeddedBrowser;

import org.openqa.selenium.By;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.WebDriverException;
import org.openqa.selenium.WebElement;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/**
 * A normalized snapshot of data entry points visible in a browser state.
 */
public final class DepSignature {

	private final List<String> entries;

	private DepSignature(List<String> entries) {
		List<String> sortedEntries = new ArrayList<>(entries);
		Collections.sort(sortedEntries);
		this.entries = Collections.unmodifiableList(sortedEntries);
	}

	public static DepSignature fromBrowser(EmbeddedBrowser browser) {
		List<String> entries = new ArrayList<>();
		List<WebElement> elements = browser.getWebDriver().findElements(
				By.cssSelector("form, input, textarea, select, button, [contenteditable=''], [contenteditable='true']"));
		for (WebElement element : elements) {
			try {
				entries.add(entryFor(browser, element));
			} catch (WebDriverException ignored) {
				// The DOM can change while Crawljax is building a state. Skipping one unstable
				// element is safer than making the state construction fail.
			}
		}
		return new DepSignature(entries);
	}

	public int size() {
		return entries.size();
	}

	private static String entryFor(EmbeddedBrowser browser, WebElement element) {
		String tag = normalized(element.getTagName());
		String type = normalized(element.getAttribute("type"));
		String name = normalized(element.getAttribute("name"));
		String id = normalized(element.getAttribute("id"));
		String action = normalized(element.getAttribute("formAction"));
		String method = normalized(element.getAttribute("formMethod"));
		String xpath = xpathFor(browser, element);
		if ("form".equals(tag)) {
			action = normalized(element.getAttribute("action"));
			method = normalized(element.getAttribute("method"));
		}
		return tag + "|type=" + type + "|name=" + name + "|id=" + id + "|method=" + method
				+ "|action=" + action + "|xpath=" + xpath;
	}

	private static String xpathFor(EmbeddedBrowser browser, WebElement element) {
		if (!(browser.getWebDriver() instanceof JavascriptExecutor)) {
			return "";
		}
		Object result = ((JavascriptExecutor) browser.getWebDriver()).executeScript(
				"function xpath(e) {"
						+ "if (e.id) return '//*[@id=\"' + e.id + '\"]';"
						+ "if (e === document.body) return '/html/body';"
						+ "var ix = 0;"
						+ "var siblings = e.parentNode ? e.parentNode.childNodes : [];"
						+ "for (var i = 0; i < siblings.length; i++) {"
						+ "var s = siblings[i];"
						+ "if (s === e) return xpath(e.parentNode) + '/' + e.tagName.toLowerCase() + '[' + (ix + 1) + ']';"
						+ "if (s.nodeType === 1 && s.tagName === e.tagName) ix++;"
						+ "}"
						+ "return '';"
						+ "}"
						+ "return xpath(arguments[0]);",
				element);
		return result == null ? "" : result.toString();
	}

	private static String normalized(String value) {
		return value == null ? "" : value.trim().toLowerCase();
	}

	@Override
	public boolean equals(Object other) {
		if (!(other instanceof DepSignature)) {
			return false;
		}
		DepSignature that = (DepSignature) other;
		return entries.equals(that.entries);
	}

	@Override
	public int hashCode() {
		return Objects.hash(entries);
	}

	@Override
	public String toString() {
		return entries.toString();
	}
}
