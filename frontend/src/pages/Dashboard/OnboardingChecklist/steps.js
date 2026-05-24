import { DEFAULT_GREETING, DEFAULT_COLOR } from "./constants";

export function computeSteps(dashData, stored) {
  const wc = dashData?.widget_config || {};
  const defaultBotSuffix = " Assistant";
  const businessName = dashData?.business_name || "";
  const defaultBotName = `${businessName}${defaultBotSuffix}`;

  return [
    {
      key: "business",
      title: "Welcome & Business Info",
      description: "Confirm your business details",
      complete: !!businessName && businessName !== "My Business",
    },
    {
      key: "hours",
      title: "Set Business Hours",
      description: "Tell customers when you're available",
      complete: !!stored.hoursDone,
    },
    {
      key: "agent",
      title: "Configure AI Agent",
      description: "Set up greeting message and FAQ answers",
      complete:
        (wc.greeting_message && wc.greeting_message !== DEFAULT_GREETING) ||
        (dashData?.faq_count || 0) > 0,
    },
    {
      key: "appearance",
      title: "Customize Appearance",
      description: "Choose your brand color and widget position",
      complete:
        (wc.primary_color && wc.primary_color !== DEFAULT_COLOR) ||
        (wc.bot_name && wc.bot_name !== defaultBotName),
    },
    {
      key: "install",
      title: "Install Widget",
      description: "Add the embed code to your website",
      complete: !!stored.installedDone,
    },
    {
      key: "test",
      title: "Test It Out",
      description: "Preview and chat with your widget",
      complete: !!stored.testDone,
    },
    {
      key: "automations",
      title: "Set Up Automations",
      description: "Auto-follow-up with new leads",
      complete: !!stored.automationsDone || (dashData?.sequence_count || 0) > 0,
    },
    {
      key: "live",
      title: "You're Live!",
      description: "Your AI assistant is ready",
      complete: false,
    },
  ];
}
