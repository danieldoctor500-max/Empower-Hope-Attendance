(() => {
	const api = window.AttendanceAPI;
	window.UserFeature = {
		list(filters = {}) {
			const query = new URLSearchParams(filters);
			return api.get(`/users${query.size ? `?${query}` : ""}`);
		},
		create: (user) => api.post("/users", user),
		update: (userId, changes) => api.patch(`/users/${userId}`, changes),
		current: () => api.get("/users/me"),
	};
})();
