import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
    title: string;
    value: string | number;
    description?: string;
    icon: LucideIcon;
    trend?: {
        value: number;
        isPositive: boolean;
    };
    className?: string;
}

export function StatCard({ title, value, description, icon: Icon, trend, className }: StatCardProps) {
    return (
        <Card className={cn("overflow-hidden", className)}>
            <CardContent className="p-6">
                <div className="flex items-center justify-between space-y-0 pb-2">
                    <p className="text-sm font-medium text-muted-foreground">{title}</p>
                    <Icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="flex items-center justify-between pt-2">
                    <div className="flex flex-col gap-1">
                        <div className="text-2xl font-bold">{value}</div>
                        {description && (
                            <p className="text-xs text-muted-foreground">{description}</p>
                        )}
                    </div>
                    {trend && (
                        <div className={cn(
                            "text-xs font-medium px-2 py-1 rounded-full",
                            trend.isPositive ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                        )}>
                            {trend.isPositive ? "+" : ""}{trend.value}%
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
