package com.crawljax.examples.stateabstractions.dep;

import com.crawljax.browser.EmbeddedBrowser;
import com.crawljax.core.state.StateVertex;
import com.crawljax.core.state.StateVertexFactory;

public class DepOnlyStateVertexFactory extends StateVertexFactory {

	@Override
	public StateVertex newStateVertex(int id, String url, String name, String dom, String strippedDom,
			EmbeddedBrowser browser) {
		return new DepOnlyStateVertex(id, url, name, dom, strippedDom, DepSignature.fromBrowser(browser));
	}

	@Override
	public String toString() {
		return "dep_only";
	}
}
