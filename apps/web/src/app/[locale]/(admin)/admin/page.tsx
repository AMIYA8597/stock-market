"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/api-client";

type User = {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
};

export default function AdminDashboard() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null); // userId of the user being updated

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminApi.listUsers();
      setUsers(data);
    } catch (err: any) {
      setError(err.message || "Failed to fetch users");
    } finally {
      setLoading(false);
    }
  };

  const handleRoleChange = async (userId: string, newRole: "USER" | "ADMIN") => {
    setUpdating(userId);
    setError(null);
    try {
      const updatedUser = await adminApi.updateUserRole(userId, newRole);
      setUsers((prev) =>
        prev.map((user) => (user.id === userId ? updatedUser : user))
      );
    } catch (err: any) {
      setError(err.message || "Failed to update user role");
    } finally {
      setUpdating(null);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex justify-center items-center h-64">
        <div className="text-lg text-gray-600 dark:text-gray-300">Loading users...</div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Admin Dashboard</h1>
        <button
          onClick={fetchUsers}
          className="bg-gray-100 hover:bg-gray-200 text-gray-800 font-semibold py-2 px-4 border border-gray-400 rounded shadow dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-white dark:border-gray-600"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6" role="alert">
          <span className="block sm:inline">{error}</span>
        </div>
      )}

      <div className="overflow-x-auto bg-white dark:bg-gray-800 shadow-md rounded-lg border dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="uppercase tracking-wider border-b-2 dark:border-neutral-600 bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
            <tr>
              <th scope="col" className="px-6 py-4 font-semibold">ID</th>
              <th scope="col" className="px-6 py-4 font-semibold">Email</th>
              <th scope="col" className="px-6 py-4 font-semibold">Full Name</th>
              <th scope="col" className="px-6 py-4 font-semibold">Status</th>
              <th scope="col" className="px-6 py-4 font-semibold">Role</th>
              <th scope="col" className="px-6 py-4 font-semibold text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr
                key={user.id}
                className="border-b dark:border-neutral-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition duration-150 text-gray-800 dark:text-gray-200"
              >
                <td className="px-6 py-4 font-mono text-xs">{user.id}</td>
                <td className="px-6 py-4">{user.email}</td>
                <td className="px-6 py-4">{user.full_name || <span className="text-gray-400 italic">Not provided</span>}</td>
                <td className="px-6 py-4">
                  <span
                    className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      user.is_active 
                        ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400" 
                        : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                    }`}
                  >
                    {user.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="px-6 py-4 font-medium">
                  {user.role}
                </td>
                <td className="px-6 py-4 text-center">
                  <button
                    onClick={() => handleRoleChange(user.id, user.role === "ADMIN" ? "USER" : "ADMIN")}
                    disabled={updating === user.id}
                    className={`inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${
                      user.role === "ADMIN"
                        ? "bg-orange-600 hover:bg-orange-700"
                        : "bg-blue-600 hover:bg-blue-700"
                    }`}
                  >
                    {updating === user.id
                      ? "Updating..."
                      : user.role === "ADMIN"
                      ? "Demote to USER"
                      : "Promote to ADMIN"}
                  </button>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-8 text-gray-500 dark:text-gray-400">
                  No users found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
