export type AppEnvironment = 'development' | 'staging' | 'production';

export type PublicConfig = {
  apiBaseUrl: string;
  appEnvironment: AppEnvironment;
  supabasePublishableKey: string;
  supabaseUrl: string;
};

export type PublicConfigResult =
  | { config: PublicConfig; error: null }
  | { config: null; error: string };

function parseUrl(name: string, value: string | undefined, environment: AppEnvironment) {
  if (!value) throw new Error(`${name} is missing.`);

  const normalized = value.replace(/\/+$/, '');
  const url = new URL(normalized);

  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error(`${name} must use HTTP or HTTPS.`);
  }

  if (environment === 'production' && url.protocol !== 'https:') {
    throw new Error(`${name} must use HTTPS in production.`);
  }

  return normalized;
}

export function readPublicConfig(): PublicConfigResult {
  try {
    const rawEnvironment = process.env.EXPO_PUBLIC_APP_ENV;

    if (
      rawEnvironment !== 'development' &&
      rawEnvironment !== 'staging' &&
      rawEnvironment !== 'production'
    ) {
      throw new Error('EXPO_PUBLIC_APP_ENV must be development, staging, or production.');
    }

    const supabasePublishableKey = process.env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim();
    if (!supabasePublishableKey) {
      throw new Error('EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY is missing.');
    }

    return {
      config: {
        apiBaseUrl: parseUrl(
          'EXPO_PUBLIC_API_BASE_URL',
          process.env.EXPO_PUBLIC_API_BASE_URL,
          rawEnvironment,
        ),
        appEnvironment: rawEnvironment,
        supabasePublishableKey,
        supabaseUrl: parseUrl(
          'EXPO_PUBLIC_SUPABASE_URL',
          process.env.EXPO_PUBLIC_SUPABASE_URL,
          rawEnvironment,
        ),
      },
      error: null,
    };
  } catch (error) {
    return {
      config: null,
      error: error instanceof Error ? error.message : 'The application configuration is invalid.',
    };
  }
}
