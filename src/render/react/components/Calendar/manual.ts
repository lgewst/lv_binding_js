// Hand-written setters for props no rule can express. The generated comp.ts
// splices these into its setter table; the spec records why each one is here.

export function manualSetters({ comp, newProps, oldProps }) {
  return {
    today(today) {
      if (today && today !== oldProps.today) {
        const date = new Date(today);
        comp.setToday(date.getFullYear(), date.getMonth() + 1, date.getDate());
      }
    },
    shownMonth(month) {
      if (month && month !== oldProps.shownMonth) {
        const date = new Date(month);
        comp.setShownMonth(date.getFullYear(), date.getMonth() + 1);
      }
    },
    highLightDates(dates) {
      if (Array.isArray(dates) && dates !== oldProps.highLightDates) {
        dates = dates.map((item) => {
          const date = new Date(item);
          return [date.getFullYear(), date.getMonth() + 1, date.getDate()];
        });
        comp.setHighlightDates(dates, dates.length);
      }
    },
  };
}
