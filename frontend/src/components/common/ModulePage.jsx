import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/common/PageHeader";
import DataTable from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import { Plus, Sparkles } from "lucide-react";

/**
 * Generic module page. Renders a page header + a reusable data table.
 * Fetches from /api/collections/<resource>.
 */
export default function ModulePage({
  resource,
  title,
  subtitle,
  crumbs = ["Dashboard"],
  columns = [],
  emptyLabel,
  primaryAction = { label: "Create record", icon: Plus },
  extraContent,
}) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    api
      .get(`/collections/${resource}`)
      .then((r) => mounted && setData(r.data.data || []))
      .catch(() => mounted && setData([]))
      .finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
  }, [resource]);

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={[...crumbs, title]}
        title={title}
        subtitle={subtitle}
        actions={
          <>
            <Button variant="outline" className="border-[#E5E7EB] h-10" data-testid={`${resource}-ai`}>
              <Sparkles size={15} className="mr-2 text-gold" /> Ask AI
            </Button>
            <Button className="bg-gold hover:bg-gold-dark text-white h-10" data-testid={`${resource}-primary-action`}>
              <primaryAction.icon size={15} className="mr-2" /> {primaryAction.label}
            </Button>
          </>
        }
      />
      {extraContent}
      <DataTable
        data={data}
        columns={columns}
        loading={loading}
        emptyLabel={emptyLabel}
        testId={`${resource}-table`}
      />
    </div>
  );
}
