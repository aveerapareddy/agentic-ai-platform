/** Local dev headers forwarded to api-gateway (Session E). */

export const DEV_AUTH_HEADERS: Record<string, string> = {
  'X-Principal-Id': 'console-operator',
  'X-Tenant-Id': 'dev-tenant',
  'X-Roles': 'operator,admin',
};
