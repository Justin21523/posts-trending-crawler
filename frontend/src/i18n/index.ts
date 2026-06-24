import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { en } from './locales/en';
import { zh } from './locales/zh';

const savedLanguage = localStorage.getItem('twCrawlerLang');

i18n.use(initReactI18next).init({
  resources: {
    zh: { translation: zh },
    en: { translation: en },
  },
  lng: savedLanguage === 'en' ? 'en' : 'zh',
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false,
  },
  returnObjects: true,
});

export { i18n };
