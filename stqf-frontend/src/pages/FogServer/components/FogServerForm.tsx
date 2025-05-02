import React from 'react';
import { Modal, Form, Input, Select, message } from 'antd';
import { FogServer, FogServerFormData } from '@/types/fogServer';
import { createFogServer, updateFogServer } from '@/api/fogServer';

interface FogServerFormProps {
  visible: boolean;
  initialValues: FogServer | null;
  onClose: () => void;
}

const { Option } = Select;

const FogServerForm: React.FC<FogServerFormProps> = ({ visible, initialValues, onClose }) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const formData: FogServerFormData = {
        service_endpoint: values.service_endpoint,
        status: values.status,
      };

      if (isEdit && initialValues) {
        await updateFogServer(initialValues.id, formData);
        message.success('Update successful');
      } else {
        await createFogServer(formData);
        message.success('Creation successful');
      }
      onClose();
    } catch (error) {
      console.error('Form submission failed:', error);
    }
  };

  return (
    <Modal
      title={isEdit ? 'Edit Server' : 'Add Server'}
      open={visible}
      onOk={handleSubmit}
      onCancel={onClose}
      destroyOnClose
    >
      <Form form={form} layout='vertical' initialValues={initialValues || undefined}>
        <Form.Item
          name='service_endpoint'
          label='Service Endpoint'
          rules={[
            { required: true, message: 'Please enter service endpoint' },
            { type: 'url', message: 'Please enter a valid URL' },
          ]}
        >
          <Input placeholder='Please enter service endpoint URL' />
        </Form.Item>

        <Form.Item
          name='status'
          label='Status'
          rules={[{ required: true, message: 'Please select status' }]}
        >
          <Select placeholder='Please select status'>
            <Option value='online'>Online</Option>
            <Option value='offline'>Offline</Option>
            <Option value='maintenance'>Maintenance</Option>
          </Select>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default FogServerForm;
