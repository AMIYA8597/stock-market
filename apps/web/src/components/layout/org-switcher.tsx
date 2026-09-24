"use client";

import { useState } from "react";
import { Select } from "@neuroquant/ui";
import { Building, User } from "lucide-react";
// import { cn } from "@neuroquant/ui";

const organizations = [
  { id: "personal", name: "Personal Workspace", type: "personal", role: "admin" },
  { id: "company", name: "Acme Corp", type: "company", role: "viewer" },
];

interface OrgSwitcherProps {
  collapsed?: boolean;
}

export function OrgSwitcher({ collapsed }: OrgSwitcherProps) {
  const [activeOrg, setActiveOrg] = useState(organizations[0]?.id || "personal");

  const currentOrg = organizations.find((o) => o.id === activeOrg);

  if (collapsed) {
    return (
      <div className="flex h-10 w-10 items-center justify-center rounded-nq mx-auto border border-nq-border bg-nq-bg-card" title={currentOrg?.name}>
        {currentOrg?.type === "company" ? <Building className="h-4.5 w-4.5 text-nq-text-secondary" /> : <User className="h-4.5 w-4.5 text-nq-text-secondary" />}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1 px-4 py-3 border-b border-nq-border">
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded bg-nq-bg-card border border-nq-border">
          {currentOrg?.type === "company" ? <Building className="h-4 w-4 text-nq-text-secondary" /> : <User className="h-4 w-4 text-nq-text-secondary" />}
        </div>
        <Select
          value={activeOrg}
          onChange={(e) => setActiveOrg(e.target.value)}
          className="h-8 py-1 text-sm bg-transparent border-none flex-1 focus-visible:ring-0 px-1 cursor-pointer font-medium"
        >
          {organizations.map((org) => (
            <option key={org.id} value={org.id}>
              {org.name}
            </option>
          ))}
        </Select>
      </div>
      <div className="text-xs text-nq-text-tertiary px-10">
        Role: <span className="font-medium text-nq-text-secondary capitalize">{currentOrg?.role}</span>
      </div>
    </div>
  );
}
