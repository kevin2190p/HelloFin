/**
 * Fakeout — AWS Lambda function: risk-event ingestion
 *
 * Runtime: Node.js 20.x (or 18.x)
 * Region:  ap-southeast-5 (Asia Pacific, Malaysia)
 *
 * Triggered by: Amazon API Gateway HTTP API, route POST /risk-event
 *
 * Receives anonymized risk metadata from a Fakeout client, validates it,
 * logs it to CloudWatch Logs, and (when risk is critical) publishes an SMS
 * alert via Amazon SNS to pre-registered family-member phone numbers.
 *
 * Audio and full transcript are NEVER sent to this function — the client
 * only forwards risk metadata.
 *
 * Required IAM permissions on this function's execution role:
 *   - sns:Publish (Resource: "*" is fine for direct phone-number publishing)
 *
 * Required environment variables:
 *   - ALERT_PHONE_NUMBERS  : E.164 numbers, comma-separated. e.g. +60123456789,+60198765432
 *   - SNS_REGION           : (optional) defaults to ap-southeast-1 (Singapore).
 *                            Use a region that supports SMS — ap-southeast-5
 *                            does NOT yet support SNS SMS as of 2026.
 *   - ALERT_RISK_THRESHOLD : (optional) numeric, default 80.
 */

import { SNSClient, PublishCommand } from "@aws-sdk/client-sns";

// SNS client lives outside the handler so it's reused across warm invocations.
// Region intentionally separate from Lambda's region because SMS support is
// not yet available in ap-southeast-5 (Malaysia).
const snsClient = new SNSClient({
  region: process.env.SNS_REGION || "ap-southeast-1"
});

const ALERT_THRESHOLD = Number(process.env.ALERT_RISK_THRESHOLD || 80);

/**
 * Build a concise SMS body (<= 160 chars to stay in one segment).
 * Mentions risk level, top reasons, and time. NO transcript / NO PII.
 */
function buildSmsBody(body) {
  const score = Math.round(Number(body.riskScore) || 0);
  const reasons = Array.isArray(body.reasonCodes) ? body.reasonCodes : [];
  const topReasons = reasons
    .slice(0, 2)
    .map((r) => String(r).toLowerCase().replace(/_/g, " "))
    .join(", ");

  // Malaysia time (UTC+8) for the SMS timestamp
  const myt = new Date(Date.now() + 8 * 60 * 60 * 1000)
    .toISOString()
    .slice(11, 16);

  return (
    `Fakeout Alert: critical scam call detected. Risk ${score}/100` +
    (topReasons ? ` (${topReasons})` : "") +
    `. ${myt} MYT. Please call your family member NOW.`
  );
}

/**
 * Publish SMS to all numbers in ALERT_PHONE_NUMBERS env var, in parallel.
 * Skipped silently when threshold not met or env var empty.
 */
async function publishFamilyAlertIfCritical(body) {
  if (typeof body.riskScore !== "number" || body.riskScore < ALERT_THRESHOLD) {
    return { sent: false, reason: "below_threshold", deliveries: [] };
  }

  const phones = (process.env.ALERT_PHONE_NUMBERS || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  if (phones.length === 0) {
    return { sent: false, reason: "no_recipients_configured", deliveries: [] };
  }

  const message = buildSmsBody(body);

  const results = await Promise.allSettled(
    phones.map((phone) =>
      snsClient.send(
        new PublishCommand({
          PhoneNumber: phone,
          Message: message,
          MessageAttributes: {
            "AWS.SNS.SMS.SMSType": {
              DataType: "String",
              StringValue: "Transactional"
            },
            "AWS.SNS.SMS.SenderID": {
              DataType: "String",
              StringValue: "FAKEOUT"
            }
          }
        })
      )
    )
  );

  const deliveries = results.map((r, i) => {
    // Mask the middle of the phone number in the response so it's not echoed in full.
    const masked = phones[i].replace(/(\+\d{2})(\d+)(\d{3})/, (_, a, mid, c) => `${a}${"*".repeat(mid.length)}${c}`);
    if (r.status === "fulfilled") {
      return { phone: masked, ok: true, messageId: r.value.MessageId };
    }
    return {
      phone: masked,
      ok: false,
      error: (r.reason && r.reason.message) || "unknown SNS error"
    };
  });

  return {
    sent: deliveries.some((d) => d.ok),
    reason: "published",
    message,
    deliveries
  };
}

export const handler = async (event, context) => {
  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "OPTIONS,POST",
    "Content-Type": "application/json"
  };

  // Handle CORS preflight
  const method = event.requestContext?.http?.method || event.httpMethod;
  if (method === "OPTIONS") {
    return { statusCode: 204, headers: corsHeaders, body: "" };
  }

  try {
    const body = typeof event.body === "string" ? JSON.parse(event.body) : event.body;

    if (!body || typeof body.riskScore !== "number") {
      return {
        statusCode: 400,
        headers: corsHeaders,
        body: JSON.stringify({
          provider: "AWS",
          status: "error",
          message: "Invalid payload. riskScore is required."
        })
      };
    }

    // Reject any payload that mistakenly contains audio/transcript
    const banned = ["audio", "audioBase64", "transcript", "fullTranscript"];
    for (const k of banned) {
      if (k in body) {
        return {
          statusCode: 400,
          headers: corsHeaders,
          body: JSON.stringify({
            provider: "AWS",
            status: "error",
            message: `Forbidden field: ${k}. Audio/transcript must stay on-device.`
          })
        };
      }
    }

    const response = {
      provider: "AWS",
      region: process.env.AWS_REGION || "ap-southeast-5",
      service: "API Gateway → Lambda → CloudWatch",
      status: "processed",
      message: "Risk event received and logged in AWS CloudWatch.",
      eventId: body.eventId || "unknown-event",
      riskScore: body.riskScore,
      riskLevel: body.riskLevel,
      reasonCodes: body.reasonCodes || [],
      audioShared: body.audioShared === true,
      transcriptShared: body.transcriptShared === true,
      awsRequestId: context.awsRequestId,
      processedAt: new Date().toISOString()
    };

    // CloudWatch log line — searchable proof for judges
    console.log(
      "Fakeout risk event:",
      JSON.stringify({
        ...body,
        processedBy: "AWS Lambda",
        awsRequestId: context.awsRequestId,
        processedAt: response.processedAt
      })
    );

    // Family-member SMS alert via Amazon SNS (only when risk is critical).
    // Wrapped in try/catch so SMS failures never break the main response.
    try {
      const familyAlert = await publishFamilyAlertIfCritical(body);
      response.familyAlert = familyAlert;
      console.log(
        "Fakeout family alert:",
        JSON.stringify({
          eventId: response.eventId,
          sent: familyAlert.sent,
          reason: familyAlert.reason,
          deliveries: familyAlert.deliveries
        })
      );
    } catch (snsErr) {
      console.error("Fakeout SNS publish failed:", snsErr);
      response.familyAlert = {
        sent: false,
        reason: "sns_error",
        error: snsErr.message
      };
    }

    return {
      statusCode: 200,
      headers: corsHeaders,
      body: JSON.stringify(response)
    };
  } catch (error) {
    console.error("Fakeout AWS Lambda error:", error);

    return {
      statusCode: 500,
      headers: corsHeaders,
      body: JSON.stringify({
        provider: "AWS",
        status: "error",
        message: "Failed to process risk event.",
        error: error.message
      })
    };
  }
};
