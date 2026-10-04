def test_match_uuid():
    import sys; sys.path.insert(0, "backend")
    from app.integrations.vcenter.client import match_vm_to_server
    class S: pass
    s = S(); s.id = "srv1"; s.system_uuid = "ABC-123"; s.hostname = "web1"; s.primary_ip = "10.0.0.5"
    assert match_vm_to_server({"instance_uuid": "abc-123", "hostname": "", "ips": []}, [s]) == ("srv1", 100)
    assert match_vm_to_server({"instance_uuid": "zzz", "hostname": "web1", "ips": []}, [s]) == ("srv1", 90)
    assert match_vm_to_server({"instance_uuid": "zzz", "hostname": "otro", "ips": ["10.0.0.5"]}, [s]) == ("srv1", 70)
