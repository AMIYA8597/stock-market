/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import { useEffect, useMemo, useState } from "react";
import { MoreHorizontal, Search } from "lucide-react";
import { Badge } from "@neuroquant/ui";
import { DataTable, type Column } from "@neuroquant/ui";
import {
  Dropdown,
  DropdownContent,
  DropdownItem,
  DropdownTrigger,
} from "@neuroquant/ui";
import { Input } from "@neuroquant/ui";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@neuroquant/ui";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@neuroquant/ui";
import { adminApi } from "@/lib/api-client";
import { useToastStore } from "@/stores/toast-store";
import { useAdminUsersQuery, useAdminContentQuery } from "@/hooks/queries/useAdmin";

interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: "Owner" | "Admin" | "Analyst";
  status: "Active" | "Invited" | "Suspended";
}



export function AdminPanelPage(): JSX.Element {
  const pushToast = useToastStore((state) => state.pushToast);
  const [query, setQuery] = useState("");

  const { data: apiUsers = [] } = useAdminUsersQuery();
  const { data: content = { posts: [] } } = useAdminContentQuery();

  const users = useMemo(
    () =>
      apiUsers.map((item) => ({
        id: item.id,
        name: item.full_name ?? item.email,
        email: item.email,
        role: item.role === "ADMIN" ? ("Admin" as const) : ("Analyst" as const),
        status: item.is_active ? ("Active" as const) : ("Suspended" as const),
      })),
    [apiUsers]
  );

  const contentRows = useMemo(
    () =>
      content.posts.map((post) => ({
        id: post.id,
        title: post.title,
        status: post.status === "published" ? "Published" : "Draft",
        author: "Editorial",
        updatedAt: "recent",
      })),
    [content.posts]
  );

  const filtered = useMemo(
    () =>
      users.filter(
        (item) =>
          item.name.toLowerCase().includes(query.toLowerCase()) ||
          item.email.toLowerCase().includes(query.toLowerCase()),
      ),
    [query, users],
  );

  const columns: Column<AdminUser>[] = [
    {
      key: "name",
      label: "Name",
      render: (_, row) => (
        <div>
          <p className="font-medium">{row.name}</p>
          <p className="text-xs text-[var(--ds-text-muted)]">{row.email}</p>
        </div>
      ),
    },
    {
      key: "role",
      label: "Role",
      render: (_, row) => (
        <Badge
          variant={
            row.role === "Owner"
              ? "buy"
              : row.role === "Admin"
                ? "default"
                : "secondary"
          }
        >
          {row.role}
        </Badge>
      ),
    },
    {
      key: "status",
      label: "Status",
      render: (_, row) => (
        <Badge
          variant={
            row.status === "Active"
              ? "buy"
              : row.status === "Invited"
                ? "neutral"
                : "sell"
          }
        >
          {row.status}
        </Badge>
      ),
    },
    {
      key: "actions",
      label: "Actions",
      align: "right",
      render: () => (
        <Dropdown>
          <DropdownTrigger asChild>
            <button className="rounded-[var(--ds-radius-lg)] p-1.5 text-[var(--ds-text-secondary)] hover:bg-[var(--ds-surface-2)]">
              <MoreHorizontal className="h-4 w-4" />
            </button>
          </DropdownTrigger>
          <DropdownContent align="end">
            <DropdownItem>Edit user</DropdownItem>
            <DropdownItem>Change role</DropdownItem>
            <DropdownItem>Deactivate</DropdownItem>
          </DropdownContent>
        </Dropdown>
      ),
    },
  ];

  return (
    <Card className="bg-[var(--ds-surface-1)]/90">
      <CardHeader>
        <CardTitle>User Management</CardTitle>
        <CardDescription>
          Admin controls for users and content workflows.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="users">
          <TabsList>
            <TabsTrigger value="users">User Management</TabsTrigger>
            <TabsTrigger value="content">Content Control</TabsTrigger>
          </TabsList>

          <TabsContent value="users">
            <div className="mb-4 mt-4 flex w-full max-w-sm items-center gap-2 rounded-[var(--ds-radius-lg)] border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)] px-3">
              <Search className="h-4 w-4 text-[var(--ds-text-muted)]" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search users"
                className="border-none bg-transparent px-0 focus-visible:ring-0"
              />
            </div>
            <DataTable columns={columns} data={filtered} rowKey="id" />
          </TabsContent>

          <TabsContent value="content" className="mt-4">
            <DataTable
              rowKey="id"
              data={contentRows}
              columns={[
                {
                  key: "title",
                  label: "Content",
                  render: (_, row) => (
                    <div>
                      <p className="font-medium">{row.title}</p>
                      <p className="text-xs text-[var(--ds-text-muted)]">
                        {row.id}
                      </p>
                    </div>
                  ),
                },
                { key: "author", label: "Author" },
                {
                  key: "status",
                  label: "Status",
                  render: (_, row) => (
                    <Badge
                      variant={
                        row.status === "Published"
                          ? "buy"
                          : row.status === "Draft"
                            ? "secondary"
                            : "neutral"
                      }
                    >
                      {row.status}
                    </Badge>
                  ),
                },
                { key: "updatedAt", label: "Last Updated" },
              ]}
            />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
