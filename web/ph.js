// PostHog, same project + settings as altmbr.com (altmbr/personalwebsite app/providers.tsx), so the index's
// traffic sits next to the rest of the site. Sends through altmbr.com's first-party /ingest proxy (this page
// is served on www.altmbr.com). The key is PostHog's public browser key, already shipped in altmbr.com's bundle.
// Off on localhost so local testing doesn't pollute the data.
(function () {
  if (!/(^|\.)altmbr\.com$/.test(location.hostname)) { window.posthog = { capture() {}, identify() {}, register() {} }; return; }
  // Official posthog-js loader stub (queues calls until array.js loads)
  !function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="init capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey getNextSurveyStep identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty createPersonProfile opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing debug".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
  const pageType = () => /\/robot-deployment-index\/companies\/./.test(location.pathname) ? 'robot_index_company'
    : /\/robot-deployment-index\/companies\/?$/.test(location.pathname) ? 'robot_index_hub' : 'robot_index';
  window.posthog.init('phc_qThXbjcFxLZaGUUtWqiSWeQkXZREedHECav3QdhiE8U8', {
    api_host: '/ingest', ui_host: 'https://us.posthog.com',
    person_profiles: 'identified_only', capture_pageview: 'history_change', capture_pageleave: true,
    autocapture: true, capture_heatmaps: true, capture_performance: { web_vitals: true }, capture_exceptions: true,
    session_recording: { maskAllInputs: true },
    before_send: (e) => { if (e) e.properties = { ...(e.properties || {}), page_type: pageType() }; return e; },
  });
})();
