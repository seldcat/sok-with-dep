package com.crawljax.examples.stateabstractions.dep;

import com.crawljax.browser.EmbeddedBrowser;
import com.crawljax.core.state.StateVertex;
import com.crawljax.core.state.StateVertexFactory;

public class DepAwareStateVertexFactory extends StateVertexFactory {

	private final StateVertexFactory delegate;

	public DepAwareStateVertexFactory(StateVertexFactory delegate) {
		this.delegate = delegate;
	}

	@Override
	public StateVertex newStateVertex(int id, String url, String name, String dom, String strippedDom,
			EmbeddedBrowser browser) {
		StateVertex state = delegate.newStateVertex(id, url, name, dom, strippedDom, browser);
		return new DepAwareStateVertex(state, DepSignature.fromBrowser(browser));
	}

	@Override
	public String toString() {
		return delegate.toString() + "_dep";
	}
}
