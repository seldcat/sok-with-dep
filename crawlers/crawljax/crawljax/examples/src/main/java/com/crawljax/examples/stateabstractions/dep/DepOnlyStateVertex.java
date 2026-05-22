package com.crawljax.examples.stateabstractions.dep;

import com.crawljax.core.state.StateVertex;
import com.crawljax.core.state.StateVertexImpl;
import com.google.common.base.MoreObjects;

public class DepOnlyStateVertex extends StateVertexImpl {

	private static final long serialVersionUID = 123400017983491L;

	private final DepSignature depSignature;

	public DepOnlyStateVertex(int id, String url, String name, String dom, String strippedDom,
			DepSignature depSignature) {
		super(id, url, name, dom, strippedDom);
		this.depSignature = depSignature;
	}

	@Override
	public boolean equals(Object object) {
		if (!(object instanceof DepOnlyStateVertex)) {
			return false;
		}
		DepOnlyStateVertex other = (DepOnlyStateVertex) object;
		return depSignature.equals(other.depSignature);
	}

	@Override
	public int hashCode() {
		return depSignature.hashCode();
	}

	@Override
	public boolean inThreshold(StateVertex vertexOfGraph) {
		return equals(vertexOfGraph);
	}

	@Override
	public double getDist(StateVertex vertexOfGraph) {
		return equals(vertexOfGraph) ? 0.0 : 1.0;
	}

	public int getDepCount() {
		return depSignature.size();
	}

	@Override
	public String toString() {
		return MoreObjects.toStringHelper(this)
				.add("id", getId())
				.add("name", getName())
				.add("deps", getDepCount())
				.toString();
	}
}
