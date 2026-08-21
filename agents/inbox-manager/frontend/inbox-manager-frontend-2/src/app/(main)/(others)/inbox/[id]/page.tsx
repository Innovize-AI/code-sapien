"use client"

import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ArrowLeft, AlertTriangle, Bot, Send, Pencil, Check } from "lucide-react";
import { cn } from "@/utils/cn";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useRouter } from 'next/navigation';
import { useRow } from "@/context/emailRow";
import { Textarea } from "@/components/ui/text-area";

// Using the mock data temporarily - in a real app, this would come from an API
const mockEmails = [
  {
    id: "1",
    subject: "Product Demo Request",
    sender: "john.doe@company.com",
    preview: "I would like to schedule a demo of your product...",
    timestamp: "10:30 AM",
    priority: "high" as const,
    intent: "inquiry" as const,
    read: false,
    mailbox: "Gmail",
    content: `
      <p>Hello,</p>
      <p>I would like to schedule a demo of your product. Our team is looking for a solution to streamline our email management process, and your product seems to fit our needs perfectly.</p>
      <p>Could you please provide some available time slots for next week?</p>
      <p>Best regards,<br>John Doe</p>
    `,
    confidenceScore: 0.89,
    needsHumanEscalation: true,
    escalationReason: "Complex product demo scheduling request",
    aiResponse: {
      summary: "Client requesting product demo for email management solution",
      suggestedAction: "Schedule demo presentation",
      keyPoints: [
        "Team needs email management solution",
        "Requesting available time slots for next week",
        "Potential lead for email management product"
      ],
      sentiment: "positive",
      priority: "high"
    }
  },
  {
    id: "2",
    subject: "Follow-up on Previous Discussion",
    sender: "sarah.smith@example.com",
    preview: "Following up on our conversation from last week...",
    timestamp: "Yesterday",
    priority: "medium" as const,
    intent: "followup" as const,
    read: true,
    content: `
      <p>Hi there,</p>
      <p>I wanted to follow up on our conversation from last week regarding the implementation timeline. Have you had a chance to review the proposal?</p>
      <p>Looking forward to your response.</p>
      <p>Best,<br>Sarah</p>
    `,
  },
  {
    id: "3",
    subject: "Technical Support Needed",
    sender: "tech.support@client.com",
    preview: "We're experiencing issues with the integration...",
    timestamp: "2 days ago",
    priority: "high" as const,
    intent: "support" as const,
    read: true,
    content: `
      <p>Hello Support Team,</p>
      <p>We're experiencing some issues with the API integration. The endpoints are returning 500 errors intermittently.</p>
      <p>Could you please look into this as soon as possible?</p>
      <p>Thanks,<br>Tech Team</p>
    `,
  },
];

export default function Page() {
  const { row, setRow } = useRow();

  const router= useRouter()
  
  // const { toast } = useToast();
  const [isEditing, setIsEditing] = useState(false);
  const [aiResponse, setAiResponse] = useState(
    row?.email_response_draft || ""
  );
  const [isButtonDisabled, setIsButtonDisabled] =useState(row?.email_sent)

  const [loading, setLoading] = useState(false);
  const [responseMessage, setResponseMessage] = useState("");

  const handleOnBackClicked:any=()=>{
    router.push("/inbox")
  }

  useEffect(()=>{
    
  },[isButtonDisabled])

  const handleSend= async()=>{
    const base_url=  process.env.NEXT_PUBLIC_BACKEND_URL
    const endpoint_url= `${base_url}/generate-draft/trigger-n8n/`

    //const handleSubmit = async () => {
    setLoading(true);

    try {
      const response = await fetch(endpoint_url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          thread_id: row?.thread_id,
          email_draft: aiResponse,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setResponseMessage(data.message);
        setIsButtonDisabled(true)
      } else {
        setResponseMessage("Something went wrong!");
      }
    } catch (error) {
      console.error("Error:", error);
      setResponseMessage("An error occurred.");
    } finally {
      setLoading(false);
    }
  }

  const handleSaveSummary = () => {
    // In a real app, this would make an API call to update the summary
    // toast({
    //   title: "AI Response Updated",
    //   description: "The AI response has been updated successfully.",
    // });
    setIsEditing(false);
    // Here you would typically update the server with the new summary
    console.log("New summary:", aiResponse);
  };
  // const email = mockEmails.find((e) => e.id === id);
  console.log("row fromm inbox id" , row)


  if (!row) {
    return (
      <div className="p-4">
        <Link to="/">
          <Button variant="ghost" className="mb-4" onClick={handleOnBackClicked}>
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Inbox
          </Button>
        </Link>
        <p>Email not found</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 max-w-4xl">
      {/* <Link to="/">
        <div className="flex items-center justify-between mb-4">
        <Link to="/">
          <Button variant="ghost">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Inbox
          </Button>
        </Link>
        <Button onClick={handleSend}>
          <Send className="mr-2 h-4 w-4" /> Send
        </Button>
      </div>
      </Link> */}
      <div className="flex items-center justify-between mb-4">
      <Button variant="ghost" className="mb-4" onClick={handleOnBackClicked}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Inbox
        </Button>
        <Button onClick={handleSend} disabled= {isButtonDisabled}>
         {!isButtonDisabled} && <Send className="mr-2 h-4 w-4" /> Send
        </Button>
      </div>
    
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold mb-2">{row.subject}</h1>
          <div className="flex items-center gap-2 mb-2">
            <p className="text-muted-foreground">From: {row.sender_email}</p>
            {/* <Badge variant="outline">{email.mailbox}</Badge> */}
          </div>
          <div>
          <div className="flex items-center gap-4">
          <p className="text-muted-foreground"> Category :  </p>
          <p className="text-muted-foreground">{row.category}</p></div>
                  </div>
           
          
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold mb-2">Email Content</h2>
              <div className="prose prose-sm max-w-none">
                { <div dangerouslySetInnerHTML={{ __html: row.preprocessed_email }} /> }
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bot className="h-5 w-5" />
                  AI Analysis
                </CardTitle>
                <CardDescription>
                  Automated analysis and suggestions
                </CardDescription>
                {row.escalated_to_human && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Human Escalation Needed</AlertTitle>
                <AlertDescription>{row.escalated_to_human}</AlertDescription>
              </Alert>
            )}
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h3 className="text-sm font-medium mb-2">Category Confidence Score</h3>
                  <div className="flex items-center gap-4">
                    <Progress
                      value={row.category_confidence_score ? row.category_confidence_score * 100 : 0}
                      className="w-full"
                    />
                    <span className="text-sm font-medium">
                      {row.category_confidence_score
                        ? `${(row.category_confidence_score * 100).toFixed(1)}%`
                        : "N/A"}
                    </span>
                  </div>
                </div>

                {row.email_response_draft && (
                  <>
                    <div>
                      <h3 className="text-sm font-medium mb-2">AI Response</h3>
                        {!isEditing ? (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setIsEditing(true)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                        ) : (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={handleSaveSummary}
                          >
                            <Check className="h-4 w-4" />
                          </Button>
                        )}
                      {isEditing ? (
                        <Textarea
                          value={aiResponse}
                          onChange={(e) => setAiResponse(e.target.value)}
                          className="w-full"
                          rows={3}
                        />
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          {aiResponse || row.email_response_draft}
                        </p>
                      )}
                    </div>

                    <div>
                      <h3 className="text-sm font-medium mb-2">Key Points</h3>
                      {/* <ul className="list-disc pl-4 text-sm text-muted-foreground">
                        {email.aiResponse.keyPoints.map((point, index) => (
                          <li key={index}>{point}</li>
                        ))}
                      </ul> */}
                    </div>

                    <div>
                      <h3 className="text-sm font-medium mb-2">Suggested Action</h3>
                      {/* <p className="text-sm text-muted-foreground">
                        {row.aiResponse.suggestedAction}
                      </p> */}
                    </div>

                    <div className="flex gap-2">
                      {/* <Badge>{email.aiResponse.sentiment}</Badge>
                      <Badge variant="secondary">
                        Priority: {email.aiResponse.priority}
                      </Badge> */}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            
          </div>
        </div>
      </div>
    </div>
  );
};
