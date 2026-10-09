(() => {
	const tokenKey = "empowerHope.accessToken";

	async function request(path, options = {}) {
		const headers = new Headers(options.headers || {});
		const token = localStorage.getItem(tokenKey);
		if (token) headers.set("Authorization", `Bearer ${token}`);
		if (options.body && !(options.body instanceof FormData)) {
			headers.set("Content-Type", "application/json");
			options.body = JSON.stringify(options.body);
		}

		const response = await fetch(`/api/v1${path}`, { ...options, headers });
		if (response.status === 204) return null;
		const contentType = response.headers.get("content-type") || "";
		const payload = contentType.includes("application/json") ? await response.json() : await response.text();
		if (!response.ok) {
			const detail = typeof payload === "object" ? payload.detail : payload;
			if (response.status === 401) localStorage.removeItem(tokenKey);
			const messages = Array.isArray(detail)
				? detail.map((item) => {
					if (item.loc?.includes("student_id") && item.type === "string_pattern_mismatch") {
						return "Student ID can contain only letters, numbers, and hyphens (no spaces).";
					}
					return item.msg;
				})
				: [];
			throw new Error(messages.length ? messages.join("; ") : detail || "Request failed");
		}
		return payload;
	}

	window.AttendanceAPI = {
		tokenKey,
		get: (path) => request(path),
		post: (path, body) => request(path, { method: "POST", body }),
		put: (path, body) => request(path, { method: "PUT", body }),
		patch: (path, body) => request(path, { method: "PATCH", body }),
		delete: (path) => request(path, { method: "DELETE" }),
		async login(identifier, password) {
			const result = await request("/auth/login", {
				method: "POST",
				body: { identifier, password },
			});
			localStorage.setItem(tokenKey, result.access_token);
			return result;
		},
		async register(data) {
			const result = await request("/auth/register", {
				method: "POST",
				body: data,
			});
			localStorage.setItem(tokenKey, result.access_token);
			return result;
		},
		async registerWithOAuth(data) {
			const result = await request("/auth/register/oauth", {
				method: "POST",
				body: data,
			});
			localStorage.setItem(tokenKey, result.access_token);
			return result;
		},
		storeToken(token) {
			localStorage.setItem(tokenKey, token);
		},
		async download(path, filename) {
			const token = localStorage.getItem(tokenKey);
			const response = await fetch(`/api/v1${path}`, {
				headers: token ? { Authorization: `Bearer ${token}` } : {},
			});
			if (!response.ok) throw new Error("Could not download report");
			const blob = await response.blob();
			const url = URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = url;
			link.download = filename;
			link.click();
			URL.revokeObjectURL(url);
		},
	};
})();
