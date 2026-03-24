const isDev = import.meta.env.DEV;

export const logger = {
    error: (...args) => {
        if (isDev) {
            console.error(...args);
        }
    },
    warn: (...args) => {
        if (isDev) {
            console.warn(...args);
        }
    },
    log: (...args) => {
        if (isDev) {
            console.log(...args);
        }
    },
    info: (...args) => {
        if (isDev) {
            console.info(...args);
        }
    }
};

export default logger;
