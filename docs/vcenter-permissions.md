# Permisos mínimos vCenter 7 (usuario solo-lectura)
Rol clonado de Read-Only + propagar a Datacenter/Cluster:
- System.View, System.Read, System.Anonymous
- VirtualMachine.GuestOperations.Query (hostname/IP/MAC Tools)
- VirtualMachine.SnapshotManagement.View? (ver snapshots; con Read-Only basta en 7.0)
- Datastore.Browse (capacidad)
- Performance.ModifyIntervals (opcional, contadores perf)
Crear en SSO → asignar en inventario con Propagate. Probar con POST /api/vcenters/{id}/test.
