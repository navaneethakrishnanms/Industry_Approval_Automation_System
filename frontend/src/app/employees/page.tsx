'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export default function EmployeesPage() {
  const [employees, setEmployees] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.employees({ page: '1', page_size: '50' });
        setEmployees(data.items || []);
        setTotal(data.total || 0);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="page-content">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="section-title" style={{ fontSize: 20, fontWeight: 800 }}>Employee Registry</h1>
          <div className="section-sub">{total} registered corporate employees</div>
        </div>
      </div>

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Email</th>
              <th>Designation</th>
              <th>Grade</th>
              <th>Role</th>
              <th>Budget Limit</th>
              <th>Leave Balance</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>Loading employees...</td></tr>
            ) : employees.length === 0 ? (
              <tr><td colSpan={8} style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>No employees found.</td></tr>
            ) : (
              employees.map(emp => (
                <tr key={emp.id}>
                  <td><span className="text-mono" style={{ color: 'var(--accent-1)' }}>{emp.employee_id}</span></td>
                  <td style={{ fontWeight: 600 }}>{emp.name}</td>
                  <td>{emp.email}</td>
                  <td>{emp.designation}</td>
                  <td><span className="badge badge-idle" style={{ fontFamily: 'JetBrains Mono' }}>{emp.grade}</span></td>
                  <td>
                    <span className={`badge ${emp.role === 'manager' ? 'badge-running' : emp.role === 'hr_admin' ? 'badge-paused' : emp.role === 'finance_admin' ? 'badge-approved' : 'badge-idle'}`}>
                      {emp.role}
                    </span>
                  </td>
                  <td className="text-mono" style={{ fontWeight: 600 }}>₹{emp.budget_limit?.toLocaleString()}</td>
                  <td className="text-mono" style={{ textAlign: 'center' }}>{emp.leave_balance} Days</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
