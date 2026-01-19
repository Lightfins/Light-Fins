import React from 'react';

const PolicyholderForm = ({ onNext, onPrev, data, updateData }) => {
    const handleChange = (e) => {
        const { name, value } = e.target;
        updateData({ [name]: value });
    };

    return (
        <div className="wizard-step policyholder-step">
            <h2>3. Policyholder Details</h2>
            <div className="form-grid">
                <div className="form-group">
                    <label>Title</label>
                    <select name="title" value={data?.title || ''} onChange={handleChange}>
                        <option value="">Select...</option>
                        <option value="Mr">Mr</option>
                        <option value="Mrs">Mrs</option>
                        <option value="Ms">Ms</option>
                        <option value="Dr">Dr</option>
                        <option value="Prof">Prof</option>
                    </select>
                </div>

                <div className="form-group">
                    <label>First Names *</label>
                    <input type="text" name="firstNames" value={data?.firstNames || ''} onChange={handleChange} required />
                </div>

                <div className="form-group">
                    <label>Surname *</label>
                    <input type="text" name="surname" value={data?.surname || ''} onChange={handleChange} required />
                </div>

                <div className="form-group">
                    <label>SA ID Number *</label>
                    <input type="text" name="idNumber" value={data?.idNumber || ''} onChange={handleChange} maxLength={13} required />
                </div>

                <div className="form-group">
                    <label>Date of Birth</label>
                    <input type="date" name="birthDate" value={data?.birthDate || ''} onChange={handleChange} />
                </div>

                <div className="form-group">
                    <label>Gender</label>
                    <select name="gender" value={data?.gender || ''} onChange={handleChange}>
                        <option value="">Select...</option>
                        <option value="M">Male</option>
                        <option value="F">Female</option>
                    </select>
                </div>

                <div className="form-group">
                    <label>Marital Status</label>
                    <select name="maritalStatus" value={data?.maritalStatus || ''} onChange={handleChange}>
                        <option value="">Select...</option>
                        <option value="Single">Single</option>
                        <option value="Married">Married</option>
                        <option value="Divorced">Divorced</option>
                        <option value="Widowed">Widowed</option>
                    </select>
                </div>

                <div className="form-group">
                    <label>Ethnicity</label>
                    <select name="ethnicity" value={data?.ethnicity || ''} onChange={handleChange}>
                        <option value="">Select...</option>
                        <option value="Black African">Black African</option>
                        <option value="White">White</option>
                        <option value="Coloured">Coloured</option>
                        <option value="Indian">Indian</option>
                        <option value="Other">Other</option>
                    </select>
                </div>
            </div>

            <div className="section-divider">Contact Details</div>
            <div className="form-grid">
                <div className="form-group">
                    <label>Cellphone *</label>
                    <input type="tel" name="cellphone" value={data?.telephoneNumbers?.cellphone || ''}
                        onChange={(e) => updateData({ telephoneNumbers: { ...data.telephoneNumbers, cellphone: e.target.value } })} required />
                </div>
                <div className="form-group">
                    <label>Email *</label>
                    <input type="email" name="email" value={data?.telephoneNumbers?.email || ''}
                        onChange={(e) => updateData({ telephoneNumbers: { ...data.telephoneNumbers, email: e.target.value } })} required />
                </div>
            </div>

            <div className="btn-group">
                <button className="btn-secondary" onClick={onPrev}>Back</button>
                <button
                    className="btn-primary"
                    onClick={onNext}
                    disabled={!data?.firstNames || !data?.surname || !data?.idNumber}
                >
                    Next: Lives Covered
                </button>
            </div>
        </div>
    );
};

export default PolicyholderForm;
