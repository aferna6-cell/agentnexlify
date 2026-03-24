/**
 * Appointments & availability API functions.
 */
import { request } from "./_client";

export function fetchAvailability(tenantId, token) {
  return request(`/api/v1/appointments/availability/${tenantId}`, { token });
}

export function updateAvailability(tenantId, token, data) {
  return request(`/api/v1/appointments/availability/${tenantId}`, { method: "PUT", token, body: data });
}

export function fetchServiceTypes(tenantId, token) {
  return request(`/api/v1/appointments/${tenantId}/service-types`, { token });
}

export function createServiceType(tenantId, token, data) {
  return request(`/api/v1/appointments/${tenantId}/service-types`, { method: "POST", token, body: data });
}

export function deleteServiceType(tenantId, token, serviceId) {
  return request(`/api/v1/appointments/${tenantId}/service-types/${serviceId}`, { method: "DELETE", token });
}

export function fetchAppointments(tenantId, token, { startDate, endDate, status } = {}) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  if (status) params.set("status", status);
  const qs = params.toString();
  return request(`/api/v1/appointments/${tenantId}${qs ? `?${qs}` : ""}`, { token });
}

export function updateAppointment(tenantId, token, appointmentId, data) {
  return request(`/api/v1/appointments/${tenantId}/${appointmentId}`, { method: "PATCH", token, body: data });
}

export function cancelAppointment(tenantId, token, appointmentId) {
  return request(`/api/v1/appointments/${tenantId}/${appointmentId}`, { method: "DELETE", token });
}

export function setAppointmentRecurrence(tenantId, token, appointmentId, rule, endDate) {
  return request(`/api/v1/appointments/${tenantId}/${appointmentId}/recur`, { method: "POST", token, body: { rule, end_date: endDate } });
}

export function createAppointment(tenantId, token, data) {
  return request(`/api/v1/appointments/${tenantId}/dashboard-book`, { method: "POST", token, body: data });
}

export function fetchNoShowStats(tenantId, token) {
  return request(`/api/v1/appointments/no-show-stats/${tenantId}`, { token });
}
