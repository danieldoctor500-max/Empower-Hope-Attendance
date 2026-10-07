(() => {
	const api = window.AttendanceAPI;
	window.AttendanceFeature = {
		roster: (sessionId) => api.get(`/attendance/sessions/${sessionId}/roster`),
		records: (sessionId) => api.get(`/attendance/sessions/${sessionId}`),
		mark: (sessionId, records) => api.post(`/attendance/sessions/${sessionId}/mark`, { records }),
		correct: (attendanceId, changes) => api.patch(`/attendance/${attendanceId}`, changes),
	};
})();
