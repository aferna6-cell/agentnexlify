import {
  AccountCard,
  BookingPageCard,
  BusinessInformationCard,
  ClientPortalLoginCard,
  DangerZoneCard,
  QuickLinksCard,
  WebsiteScannerCard,
} from "./BusinessSettingsCards";
import {
  AgentOSAutoSendCard,
  AutoReviewRequestsCard,
  BrowserNotificationsCard,
  DailyBriefingCard,
  GoogleReviewLinkCard,
  MissedCallTextBackCard,
  VoiceAICard,
  NoShowRecoveryCard,
  SmsNotificationsCard,
} from "./MessagingSettingsCards";
import PhoneProvisioningCard from "./PhoneProvisioningCard";
import { ConversationTagsCard, CustomFieldsCard } from "./TagsAndFieldsCards";
import {
  AiKnowledgeSourcesCard,
  AiResponseFeedbackCard,
} from "./KnowledgeFeedbackCards";

export default function SettingsPageContent(props) {
  const saveProps = {
    handleSave: props.handleSave,
    saving: props.saving,
    saved: props.saved,
  };
  const formProps = {
    form: props.form,
    setForm: props.setForm,
    setSaved: props.setSaved,
  };

  return (
    <div className="settings-page-grid">
      <BusinessInformationCard
        form={props.form}
        handleChange={props.handleChange}
        saveError={props.saveError}
        {...saveProps}
      />
      <WebsiteScannerCard
        form={props.form}
        handleChange={props.handleChange}
        handleScanWebsite={props.handleScanWebsite}
        crawling={props.crawling}
        crawlStatus={props.crawlStatus}
        businessSlug={props.businessSlug}
        businessPageEnabled={props.businessPageEnabled}
        onNavigate={props.onNavigate}
        {...saveProps}
      />
      <AccountCard
        email={props.email}
        livePlan={props.livePlan}
        onNavigate={props.onNavigate}
      />
      <SmsNotificationsCard
        handleChange={props.handleChange}
        {...formProps}
        {...saveProps}
      />
      <BrowserNotificationsCard />
      <GoogleReviewLinkCard
        form={props.form}
        handleChange={props.handleChange}
        {...saveProps}
      />
      <AutoReviewRequestsCard {...formProps} {...saveProps} />
      <DailyBriefingCard {...formProps} {...saveProps} />
      <NoShowRecoveryCard {...formProps} {...saveProps} />
      <AgentOSAutoSendCard {...formProps} {...saveProps} />
      <VoiceAICard plan={props.livePlan} {...formProps} {...saveProps} />
      <MissedCallTextBackCard {...formProps} {...saveProps} />
      <PhoneProvisioningCard
        provisionedPhone={props.provisionedPhone}
        phoneAreaCode={props.phoneAreaCode}
        setPhoneAreaCode={props.setPhoneAreaCode}
        availableNumbers={props.availableNumbers}
        searchingNumbers={props.searchingNumbers}
        provisioningPhone={props.provisioningPhone}
        releasingPhone={props.releasingPhone}
        phoneError={props.phoneError}
        phoneSuccess={props.phoneSuccess}
        setAvailableNumbers={props.setAvailableNumbers}
        setPhoneError={props.setPhoneError}
        handleSearchNumbers={props.handleSearchNumbers}
        handleProvision={props.handleProvision}
        handleReleasePhone={props.handleReleasePhone}
      />
      <BookingPageCard
        apiBase={props.apiBase}
        businessSlug={props.businessSlug}
      />
      <QuickLinksCard onNavigate={props.onNavigate} />
      <ConversationTagsCard
        tagDefs={props.tagDefs}
        newTagName={props.newTagName}
        setNewTagName={props.setNewTagName}
        newTagColor={props.newTagColor}
        setNewTagColor={props.setNewTagColor}
        savingTag={props.savingTag}
        handleAddTag={props.handleAddTag}
        handleToggleTag={props.handleToggleTag}
        handleDeleteTag={props.handleDeleteTag}
      />
      <CustomFieldsCard
        cfLoadError={props.cfLoadError}
        customFieldDefs={props.customFieldDefs}
        newFieldName={props.newFieldName}
        setNewFieldName={props.setNewFieldName}
        newFieldType={props.newFieldType}
        setNewFieldType={props.setNewFieldType}
        newFieldOptions={props.newFieldOptions}
        setNewFieldOptions={props.setNewFieldOptions}
        newFieldRequired={props.newFieldRequired}
        setNewFieldRequired={props.setNewFieldRequired}
        savingField={props.savingField}
        deletingFieldId={props.deletingFieldId}
        handleAddCustomField={props.handleAddCustomField}
        handleDeleteCustomField={props.handleDeleteCustomField}
      />
      <AiKnowledgeSourcesCard
        knowledgeStats={props.knowledgeStats}
        onNavigate={props.onNavigate}
      />
      <AiResponseFeedbackCard
        feedback={props.feedback}
        handleDeleteFeedback={props.handleDeleteFeedback}
      />
      <ClientPortalLoginCard
        clientLoginEnabled={props.clientLoginEnabled}
        togglingClientLogin={props.togglingClientLogin}
        businessSlug={props.businessSlug}
        handleToggleClientLogin={props.handleToggleClientLogin}
      />
      <DangerZoneCard logout={props.logout} />
    </div>
  );
}
