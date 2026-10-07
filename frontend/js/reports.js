(() => {
	const api = window.AttendanceAPI;
	window.ReportFeature = {
		summary: () => api.get("/dashboard/summary"),
		attendance: (filters) => api.get(`/reports/attendance?${new URLSearchParams(filters)}`),
		exportAttendance: (filters) => api.download(`/reports/attendance.csv?${new URLSearchParams(filters)}`, "attendance-report.csv"),
		auditLog: (limit = 200) => api.get(`/audit-logs?limit=${limit}`),
	};
})();
