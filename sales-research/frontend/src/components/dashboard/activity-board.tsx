"use client"

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Activity, fetchActivities } from "@/lib/api";
import { 
    Calendar, 
    Mail, 
    MessageSquare, 
    BarChart3, 
    Zap, 
    Clock, 
    AlertCircle 
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

export function ActivityBoard({ className }: { className?: string }) {
    const [activities, setActivities] = useState<Activity[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    const loadActivities = async () => {
        try {
            const data = await fetchActivities(15);
            setActivities(data);
        } catch (e) {
            console.error("Failed to load activities", e);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        loadActivities();
        // Poll for updates every 30 seconds
        const interval = setInterval(loadActivities, 30000);
        return () => clearInterval(interval);
    }, []);

    const getIcon = (type: string) => {
        switch (type) {
            case "meeting": return <Calendar className="w-4 h-4 text-purple-500" />;
            case "email": return <Mail className="w-4 h-4 text-blue-500" />;
            case "comment": return <MessageSquare className="w-4 h-4 text-green-500" />;
            case "analysis": return <BarChart3 className="w-4 h-4 text-slate-500" />;
            case "high_potential": return <Zap className="w-4 h-4 text-orange-500" />;
            default: return <Clock className="w-4 h-4 text-slate-400" />;
        }
    };

    const getBgColor = (type: string) => {
        switch (type) {
            case "meeting": return "bg-purple-500/10";
            case "email": return "bg-blue-500/10";
            case "comment": return "bg-green-500/10";
            case "analysis": return "bg-slate-500/10";
            case "high_potential": return "bg-orange-500/10";
            default: return "bg-slate-500/10";
        }
    };

    return (
        <Card className={className}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 border-b">
                <div className="space-y-1">
                    <CardTitle className="text-xl font-bold">Activity Board</CardTitle>
                    <CardDescription>Real-time updates from your pipeline.</CardDescription>
                </div>
            </CardHeader>
            <CardContent className="p-0">
                <div className="space-y-4 px-6 py-4 max-h-[500px] overflow-y-auto scrollbar-thin scrollbar-thumb-muted">
                    {isLoading ? (
                        <div className="text-sm text-muted-foreground py-8 text-center">Loading activities...</div>
                    ) : activities.length === 0 ? (
                        <div className="text-sm text-muted-foreground py-8 text-center">No recent activities.</div>
                    ) : (
                        activities.map((activity) => (
                            <div key={activity.id} className="flex gap-4 items-start pb-4 border-b last:border-0 last:pb-0">
                                <div className={`p-2 rounded-full ${getBgColor(activity.type)}`}>
                                    {getIcon(activity.type)}
                                </div>
                                <div className="space-y-1 flex-1 min-w-0">
                                    <div className="flex justify-between items-start gap-2">
                                        <p className="text-sm font-medium leading-none truncate">{activity.title}</p>
                                        <time className="text-[10px] text-muted-foreground whitespace-nowrap">
                                            {formatDistanceToNow(new Date(activity.created_at), { addSuffix: true })}
                                        </time>
                                    </div>
                                    {activity.description && (
                                        <p className="text-xs text-muted-foreground line-clamp-2">
                                            {activity.description}
                                        </p>
                                    )}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
