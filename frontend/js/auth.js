(() => {
	const api = window.AttendanceAPI;
	window.AuthFeature = {
		login: (identifier, password) => api.login(identifier, password),
		register: (payload) => api.register(payload),
		registerWithOAuth: (payload) => api.registerWithOAuth(payload),
		storeToken: (token) => api.storeToken(token),
		currentUser: () => api.get("/users/me"),
		logout: () => localStorage.removeItem(api.tokenKey),
	};
})();
