"use client"

import { ColumnDef } from "@tanstack/react-table"

import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"

import { labels, priorities, statuses } from "../data/data"
import { EmailRow } from "../data/schema"
import { DataTableColumnHeader } from "./data-table-column-header"
import { DataTableRowActions } from "./data-table-row-actions"

export const columns: ColumnDef<EmailRow>[] = [
  
  {
    accessorKey: "sender_email",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Sender Email" />
    ),
    cell: ({ row }) => <div className="w-[180px]">{row.getValue("sender_email")}</div>,
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "category",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Category" />
    ),
    cell: ({ row }) => <div className="w-[80px]">{row.getValue("category")}</div>,
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "preprocessed_email",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Email" />
    ),
    cell: ({ row }) => <div className="w-[180px]">{row.getValue("preprocessed_email")}</div>,
    enableSorting: false,
    enableHiding: false,
    // cell: ({ row }) => {
    //   // const label = labels.find((label) => label.value === row.original.label)

    //   return (
    //     <div className="flex space-x-2">
    //       {/* {label && <Badge variant="outline">{label.label}</Badge>} */}
    //       <span className="max-w-[500px] truncate font-medium">
    //         {row.getValue("category")}
    //       </span>
    //     </div>
    //   )
    // },
  },
  {
    accessorKey: "email_response_draft",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Email Response" />
    ),
    cell: ({ row }) => <div className="w-[320px]">{row.getValue("email_response_draft")}</div>,
    enableSorting: false,
    enableHiding: false,
  
  },
  {
    accessorKey: "category_confidence_score",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Category Confidence Score" />
    ),
    cell: ({ row }) => <div className="w-[80px]">{row.getValue("category_confidence_score")}</div>,
    enableSorting: false,
    enableHiding: false,
  
  },
  {
    accessorKey: "escalated_to_human",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Escalated to Human" />
    ),
    cell: ({ row }) => <div className="w-[80px]">{row.getValue("escalated_to_human")}</div>,
    enableSorting: false,
    enableHiding: false,
  
  },
  // {
  //   id: "actions",
  //   cell: ({ row }) => <DataTableRowActions row={row} />,
  // },
]
