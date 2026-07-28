// Mongo init — creates a low-privilege application user if MONGO_INITDB_ROOT_USERNAME is set.
// This runs only on FIRST container start.
db = db.getSiblingDB(process.env.MONGO_INITDB_DATABASE || "go_oil_dms");
try {
  db.createUser({
    user: "gooil_app",
    pwd: "changeme",
    roles: [{ role: "readWrite", db: process.env.MONGO_INITDB_DATABASE || "go_oil_dms" }],
  });
  print("gooil_app user created");
} catch (e) {
  print("gooil_app user creation skipped: " + e.message);
}
