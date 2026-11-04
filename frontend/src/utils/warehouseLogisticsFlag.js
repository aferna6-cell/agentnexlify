// Warehouse / Logistics is not in tenants_business_type_check until
// migration 204 is applied. Keep the option off unless that flag is set.
const WAREHOUSE_LOGISTICS_VALUES = new Set([
  "warehouse_logistics",
  "warehouse",
  "logistics",
  "warehousing",
  "freight",
  "fulfillment",
  "distribution",
  "3pl",
  "third_party_logistics",
]);

export function isWarehouseLogisticsEnabled() {
  return import.meta.env.VITE_WAREHOUSE_LOGISTICS_ENABLED === "1";
}

export function isWarehouseLogisticsType(value) {
  return WAREHOUSE_LOGISTICS_VALUES.has(
    String(value || "")
      .trim()
      .toLowerCase(),
  );
}

export function businessTypeForForm(value, fallback = "other") {
  if (isWarehouseLogisticsType(value) && !isWarehouseLogisticsEnabled()) {
    return fallback;
  }
  return value || fallback;
}
