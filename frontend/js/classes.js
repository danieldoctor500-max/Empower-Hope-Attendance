(() => {
	const api = window.AttendanceAPI;
	window.ClassFeature = {
		list: () => api.get("/classes"),
		create: (classData) => api.post("/classes", classData),
		update: (classId, changes) => api.patch(`/classes/${classId}`, changes),
		assignStaff: (classId, staffId) => api.put(`/classes/${classId}/staff/${staffId}`),
		unassignStaff: (classId, staffId) => api.delete(`/classes/${classId}/staff/${staffId}`),
		enroll: (studentId, classId) => api.post("/enrollments", { student_id: studentId, class_id: classId }),
		students: () => api.get("/users?role=STUDENT&active=true"),
		staff: () => api.get("/users?role=STAFF&active=true"),
	};
})();
