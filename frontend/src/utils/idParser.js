/**
 * Parses a South African ID number to extracting birthdate, age, and gender.
 * CAUTION: This is a basic validation and extraction. Real verification requires Home Affairs lookup.
 * 
 * @param {string} idNumber - 13 digit SA ID
 * @returns {Object|null} - { birthDate: Date, age: number, gender: 'Male'|'Female', valid: boolean }
 */
export const parseSAID = (idNumber) => {
    if (!idNumber || idNumber.length !== 13 || isNaN(idNumber)) {
        return null;
    }

    // Extract parts
    const yy = idNumber.substring(0, 2);
    const mm = idNumber.substring(2, 4);
    const dd = idNumber.substring(4, 6);
    const genderCode = parseInt(idNumber.substring(6, 10));

    // Guess century (Simple heuristic: 20s are likely 2000s, 30-99 are 1900s for adults)
    // For a funeral plan app, we assume adults.
    const currentYear = new Date().getFullYear();
    const currentCentury = Math.floor(currentYear / 100) * 100;
    const prevCentury = currentCentury - 100;

    let year = parseInt(yy);
    // If yy is less than current year last 2 digits, it *might* be 2000s, 
    // but for funeral plans usually it's 1900s. 
    // Let's assume if 00-24 -> 2000s (Age 0-24), 25-99 -> 1900s (Age 25+)
    // But legal age is 18.

    // Safer logic:
    let fullYear = 2000 + year;
    if (fullYear > currentYear - 18) {
        fullYear = 1900 + year; // Must be older
    }

    const birthDate = new Date(fullYear, parseInt(mm) - 1, parseInt(dd));

    // Validate date
    if (birthDate.getMonth() + 1 !== parseInt(mm) || birthDate.getDate() !== parseInt(dd)) {
        return null; // Invalid date (e.g. 31st Feb)
    }

    // Calculate Age
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const m = today.getMonth() - birthDate.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
        age--;
    }

    // Gender 
    // 0000-4999 = Female
    // 5000-9999 = Male
    const gender = genderCode < 5000 ? 'Female' : 'Male';

    return {
        birthDate,
        age,
        gender,
        valid: true
    };
};
