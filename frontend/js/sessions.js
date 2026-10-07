(() => {
	const api = window.AttendanceAPI;
	window.SessionFeature = {
		list(filters = {}) {
			const query = new URLSearchParams(filters);
			return api.get(`/sessions${query.size ? `?${query}` : ""}`);
		},
		create: (session) => api.post("/sessions", session),
		update: (sessionId, changes) => api.patch(`/sessions/${sessionId}`, changes),
		open: (sessionId) => api.post(`/sessions/${sessionId}/open`),
		close: (sessionId) => api.post(`/sessions/${sessionId}/close`),
	};
})();
