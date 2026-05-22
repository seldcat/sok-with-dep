package com.crawljax.examples.stateabstractions.dep;

import com.crawljax.core.CandidateElement;
import com.crawljax.core.state.StateVertex;
import com.crawljax.core.state.StateVertexImpl;
import com.google.common.base.MoreObjects;
import com.google.common.collect.ImmutableList;

import java.util.LinkedList;

public class DepAwareStateVertex extends StateVertexImpl {

	private static final long serialVersionUID = 123400017983490L;

	private final StateVertex delegate;
	private final DepSignature depSignature;

	public DepAwareStateVertex(StateVertex delegate, DepSignature depSignature) {
		super(delegate.getId(), delegate.getUrl(), delegate.getName(), delegate.getDom(),
				delegate.getStrippedDom());
		this.delegate = delegate;
		this.depSignature = depSignature;
	}

	@Override
	public boolean equals(Object object) {
		StateVertex otherDelegate = unwrap(object);
		if (otherDelegate == null || !delegate.equals(otherDelegate)) {
			return false;
		}
		if (!(object instanceof DepAwareStateVertex)) {
			return false;
		}
		DepAwareStateVertex other = (DepAwareStateVertex) object;
		return depSignature.equals(other.depSignature);
	}

	@Override
	public int hashCode() {
		return depSignature.hashCode();
	}

	@Override
	public boolean inThreshold(StateVertex vertexOfGraph) {
		return delegate.inThreshold(unwrapOrOriginal(vertexOfGraph));
	}

	@Override
	public double getDist(StateVertex vertexOfGraph) {
		return delegate.getDist(unwrapOrOriginal(vertexOfGraph));
	}

	@Override
	public void setElementsFound(LinkedList<CandidateElement> elements) {
		super.setElementsFound(elements);
		delegate.setElementsFound(elements);
	}

	@Override
	public ImmutableList<CandidateElement> getCandidateElements() {
		ImmutableList<CandidateElement> elements = super.getCandidateElements();
		return elements == null ? delegate.getCandidateElements() : elements;
	}

	public int getDepCount() {
		return depSignature.size();
	}

	private StateVertex unwrapOrOriginal(StateVertex vertex) {
		StateVertex unwrapped = unwrap(vertex);
		return unwrapped == null ? vertex : unwrapped;
	}

	private StateVertex unwrap(Object object) {
		if (object instanceof DepAwareStateVertex) {
			return ((DepAwareStateVertex) object).delegate;
		}
		if (object instanceof StateVertex) {
			return (StateVertex) object;
		}
		return null;
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
